"""
SENTINEL — Three-stream convergence for Ferry County wildfire corridor risk.

Atmosphere (public NOAA), canopy (local roads + treatments), ground (drought/snow/slope — degrades gracefully).
Produces ranked road segments; persists scans for history and dashboards.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import date, datetime, timezone
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.services.weather_service import get_current_weather
from backend.models.road import Road
from backend.models.sentinel import SentinelRoadRisk, SentinelScan
from backend.models.treatment import Treatment
from backend.models.waypoint import Waypoint

logger = logging.getLogger(__name__)

FERRY_COUNTY_LAT = 48.65
FERRY_COUNTY_LON = -118.6
FERRY_COUNTY_BBOX = "-119.1,48.2,-118.0,49.1"

NOAA_HEADERS = {"User-Agent": "FerryCWDG-SENTINEL/1.0 (Ferry County; emergency ops)"}

ATMOSPHERE_THRESHOLD = 65.0
CANOPY_THRESHOLD = 60.0
GROUND_SCORE_THRESHOLD = 55.0
CONVERGENCE_THRESHOLD = 2

_ATMOSPHERE_CACHE: dict[str, Any] | None = None
_ATMOSPHERE_CACHE_MONO = 0.0
ATMOSPHERE_CACHE_SEC = 3600

_GROUND_CACHE: dict[str, Any] | None = None
_GROUND_CACHE_MONO = 0.0
GROUND_CACHE_SEC = 6 * 3600

LEVEL_ORDER = {"low": 0, "moderate": 1, "elevated": 2, "critical": 3}

FERRY_COUNTY_SNOTEL_STATIONS = [
    {"id": "679", "name": "Republic"},
    {"id": "919", "name": "Wauconda Summit"},
]


def _parse_mph(s: str | None) -> float:
    if not s:
        return 0.0
    m = re.search(r"([\d.]+)\s*mph", str(s), re.I)
    if m:
        return float(m.group(1))
    m2 = re.search(r"([\d.]+)", str(s))
    return float(m2.group(1)) if m2 else 0.0


def fetch_atmosphere_signal() -> dict[str, Any]:
    """GAIA → NOAA weather bundle (15m) plus a 1h SENTINEL cache tier."""
    global _ATMOSPHERE_CACHE, _ATMOSPHERE_CACHE_MONO
    now_mono = time.monotonic()
    if _ATMOSPHERE_CACHE is not None and (now_mono - _ATMOSPHERE_CACHE_MONO) < ATMOSPHERE_CACHE_SEC:
        out = dict(_ATMOSPHERE_CACHE)
        out["confidence"] = min(float(out.get("confidence") or 1.0), 0.5)
        return out

    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        w = get_current_weather()
        rh = float(w.get("humidity_pct") or 40)
        wind_mph = float(w.get("wind_mph") or 0)
        fwi = float(w.get("fire_weather_index") or 40)
        red = bool(w.get("red_flag_warning"))
        src = str(w.get("source") or "noaa")
        moisture_deficit = max(0.0, min(1.0, (60.0 - rh) / 60.0 + wind_mph / 80.0))
        conf = 1.0 if src in ("gaia", "noaa") else 0.35
        out = {
            "fire_weather_index": round(fwi, 2),
            "wind_speed_mph": round(wind_mph, 2),
            "wind_direction_deg": 0.0,
            "relative_humidity_pct": rh,
            "moisture_deficit": round(moisture_deficit, 4),
            "red_flag_active": red,
            "forecast_window_hrs": 6,
            "source_timestamp": str(w.get("updated_at") or now_iso),
            "confidence": conf,
        }
        _ATMOSPHERE_CACHE = out
        _ATMOSPHERE_CACHE_MONO = now_mono
        return dict(out)
    except Exception as e:
        logger.warning("sentinel atmosphere degrade: %s", e)
        return {
            "fire_weather_index": 42.0,
            "wind_speed_mph": 8.0,
            "wind_direction_deg": 270.0,
            "relative_humidity_pct": 45.0,
            "moisture_deficit": 0.15,
            "red_flag_active": False,
            "forecast_window_hrs": 6,
            "source_timestamp": now_iso,
            "confidence": 0.35,
        }


def fetch_canopy_signal(db: Session) -> list[dict[str, Any]]:
    """
    Grant-road fuel load from CEMP inventory + treatments (Phase 5 spec).
    Only roads with cemp_miles > 0.
    """
    roads = db.execute(select(Road).where(Road.deleted_at.is_(None))).scalars().all()
    out: list[dict[str, Any]] = []
    today = date.today()

    for road in roads:
        cemp = float(road.cemp_miles or 0)
        if cemp <= 0:
            continue
        cbmp = float(road.cbmp_miles or 0)
        untreated_miles = max(0.0, cemp - cbmp)
        treatment_pct = min(100.0, (cbmp / cemp) * 100.0)
        fuel_load_score = min(100.0, (untreated_miles / cemp) * 100.0)

        last_tx = db.execute(
            select(func.max(Treatment.treatment_date))
            .where(Treatment.road_id == road.id)
            .where(Treatment.deleted_at.is_(None))
        ).scalar_one_or_none()
        days_since: int | None = None
        if last_tx:
            days_since = (today - last_tx).days

        if days_since is None or days_since > 730:
            regrowth = 0.6
        elif days_since > 365:
            regrowth = 0.3
        else:
            regrowth = 0.1

        struct_n = db.execute(
            select(func.count())
            .select_from(Waypoint)
            .where(Waypoint.deleted_at.is_(None))
            .where(Waypoint.road_id == road.id)
        ).scalar_one()
        adjacent = int(struct_n or 0)
        corridor_mi = float(road.length_mi or cemp or 1.0)

        out.append(
            {
                "road_id": road.id,
                "road_name": road.road_name,
                "fuel_load_score": round(fuel_load_score, 2),
                "treatment_pct": round(treatment_pct, 2),
                "days_since_treatment": days_since,
                "regrowth_factor": round(regrowth, 4),
                "adjacent_structures": adjacent,
                "corridor_length_mi": round(corridor_mi, 4),
                "untreated_miles": round(untreated_miles, 4),
            }
        )
    out.sort(key=lambda r: r["fuel_load_score"], reverse=True)
    return out


def _fetch_pdsi_cdo() -> float | None:
    token = (get_settings().noaa_cdo_token or "").strip()
    if not token:
        return None
    try:
        timeout = float(get_settings().sentinel_http_timeout_s)
        with httpx.Client(timeout=timeout, headers={"token": token}) as client:
            r = client.get(
                "https://www.ncdc.noaa.gov/cdo-web/api/v2/data",
                params={
                    "datasetid": "GSOM",
                    "locationid": "FIPS:53019",
                    "datatypeid": "PALMER",
                    "limit": 24,
                    "sortorder": "desc",
                },
            )
            if r.status_code != 200:
                return None
            results = (r.json() or {}).get("results") or []
            if not results:
                return None
            return float(results[0]["value"])
    except Exception as e:
        logger.debug("NOAA CDO PDSI: %s", e)
        return None


def _fetch_snotel_station_pct(station_triplet: str) -> float | None:
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = (
        "https://wcc.sc.egov.usda.gov/reportGenerator/view_csv/customSingleStationReport/daily/"
        f"{station_triplet}/2024-01-01:{end}|0,0|name,WTEQ::pctOfMedian_1991?fitToScreen=false"
    )
    try:
        timeout = float(get_settings().sentinel_http_timeout_s)
        with httpx.Client(timeout=timeout, headers=NOAA_HEADERS) as client:
            r = client.get(url)
            if r.status_code != 200 or not r.text:
                return None
        raw_lines = [ln.strip() for ln in r.text.splitlines() if ln.strip()]
        if len(raw_lines) < 2:
            return None
        last = raw_lines[-1].split(",")
        for part in reversed(last):
            try:
                return float(part)
            except ValueError:
                continue
    except Exception as e:
        logger.debug("SNOTEL csv %s: %s", station_triplet, e)
    return None


def fetch_ground_signal() -> dict[str, Any]:
    """Palmer (NOAA CDO when keyed) + SNOTEL + static slope index; 6h cache."""
    global _GROUND_CACHE, _GROUND_CACHE_MONO
    now_m = time.monotonic()
    if _GROUND_CACHE is not None and (now_m - _GROUND_CACHE_MONO) < GROUND_CACHE_SEC:
        out = dict(_GROUND_CACHE)
        out["confidence"] = min(float(out.get("confidence") or 1.0), 0.6)
        return out

    now_iso = datetime.now(timezone.utc).isoformat()
    palmer = -0.8
    snotel_pct = 85.0
    slope_idx = 68.0
    confidence = 0.55

    p = _fetch_pdsi_cdo()
    if p is not None:
        palmer = p
        confidence = 0.9
    else:
        palmer = -1.4
        confidence = 0.45

    p679 = _fetch_snotel_station_pct("679:WA:SNTL")
    p919 = _fetch_snotel_station_pct("919:WA:SNTL")
    vals = [x for x in (p679, p919) if x is not None]
    if vals:
        snotel_pct = float(sum(vals) / len(vals))
        confidence = max(confidence, 0.72)

    watershed = max(0.0, min(1.0, (100.0 - snotel_pct) / 120.0 + max(0.0, -palmer) / 6.0))
    soil = max(15.0, 100.0 - watershed * 80.0)

    out = {
        "palmer_drought_index": round(palmer, 2),
        "soil_moisture_pct": round(soil, 2),
        "snotel_swe_pct_normal": round(snotel_pct, 2),
        "slope_fire_risk_index": slope_idx,
        "watershed_stress": round(watershed, 4),
        "source_timestamp": now_iso,
        "confidence": confidence,
    }
    _GROUND_CACHE = out
    _GROUND_CACHE_MONO = now_m
    return dict(out)


def _risk_level_from_convergence(count: int, red_flag: bool) -> str:
    if red_flag or count >= 3:
        return "critical"
    if count == 2:
        return "elevated"
    if count == 1:
        return "moderate"
    return "low"


def _recommendation(risk_level: str, primary_driver: str, *, red_flag: bool) -> str:
    _ = primary_driver
    if risk_level == "critical":
        return (
            "Immediate attention. Untreated corridor at high ignition risk under current conditions."
            + (" Red Flag or Fire Weather alert in effect." if red_flag else "")
        )
    if risk_level == "elevated":
        return "Treatment on this corridor should be scheduled within 30 days."
    if risk_level == "moderate":
        return "Consider prioritizing treatment on this corridor this season."
    return "No immediate action required. Monitor forecast."


def calculate_road_risk_score(
    road_id: int,
    atmosphere: dict[str, Any],
    canopy: dict[str, Any],
    ground: dict[str, Any],
) -> dict[str, Any]:
    atmosphere_score = float(atmosphere.get("fire_weather_index") or 0)
    fuel = float(canopy.get("fuel_load_score") or 0)
    regrowth = float(canopy.get("regrowth_factor") or 0)
    canopy_score = fuel * (1.0 + regrowth)

    pdsi = float(ground.get("palmer_drought_index") or 0)
    ground_score = (abs(min(0.0, pdsi)) / 4.0) * 100.0
    ground_score = min(100.0, ground_score)

    atmos_ok = atmosphere_score > ATMOSPHERE_THRESHOLD
    canopy_ok = canopy_score > CANOPY_THRESHOLD
    ground_ok = ground_score > GROUND_SCORE_THRESHOLD
    conv = sum(1 for x in (atmos_ok, canopy_ok, ground_ok) if x)

    contributors = {
        "atmosphere": atmosphere_score,
        "canopy": canopy_score,
        "ground": ground_score,
    }
    primary_driver = max(contributors, key=lambda k: contributors[k])

    risk_score = (
        0.40 * atmosphere_score + 0.35 * min(100.0, canopy_score) + 0.25 * ground_score
    )
    risk_score = max(0.0, min(100.0, risk_score))

    red_flag = bool(atmosphere.get("red_flag_active"))
    risk_level = _risk_level_from_convergence(conv, red_flag)
    rec = _recommendation(risk_level, primary_driver, red_flag=red_flag)

    return {
        "road_id": road_id,
        "risk_score": round(risk_score, 2),
        "convergence_count": conv,
        "risk_level": risk_level,
        "atmosphere_contributing": atmos_ok,
        "canopy_contributing": canopy_ok,
        "ground_contributing": ground_ok,
        "primary_driver": primary_driver,
        "recommendation": rec,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


def run_convergence_scan(db: Session) -> dict[str, Any]:
    atmosphere = fetch_atmosphere_signal()
    ground = fetch_ground_signal()
    canopy_rows = fetch_canopy_signal(db)

    scan = SentinelScan(
        atmosphere_fwi=atmosphere.get("fire_weather_index"),
        atmosphere_rh=atmosphere.get("relative_humidity_pct"),
        atmosphere_wind=atmosphere.get("wind_speed_mph"),
        red_flag_active=bool(atmosphere.get("red_flag_active")),
        palmer_drought=ground.get("palmer_drought_index"),
        soil_moisture=ground.get("soil_moisture_pct"),
        scan_complete=False,
        road_count=len(canopy_rows),
    )
    db.add(scan)
    db.flush()

    risks: list[dict[str, Any]] = []
    for c in canopy_rows:
        rid = c["road_id"]
        row = calculate_road_risk_score(rid, atmosphere, c, ground)
        risks.append(row)
        db.add(
            SentinelRoadRisk(
                scan_id=scan.id,
                road_id=rid,
                risk_score=row["risk_score"],
                convergence_count=row["convergence_count"],
                risk_level=row["risk_level"],
                atmosphere_contributing=row["atmosphere_contributing"],
                canopy_contributing=row["canopy_contributing"],
                ground_contributing=row["ground_contributing"],
                primary_driver=row["primary_driver"],
                recommendation=row["recommendation"],
            )
        )

    scan.scan_complete = True
    db.commit()
    risks.sort(key=lambda r: float(r["risk_score"]), reverse=True)
    return {
        "scan_id": scan.id,
        "road_count": len(risks),
        "critical_count": sum(1 for r in risks if r["risk_level"] == "critical"),
        "risks": risks,
        "atmosphere": atmosphere,
        "ground": ground,
    }


def get_top_risk_corridors(db: Session, limit: int = 10) -> list[dict[str, Any]]:
    latest_id = db.scalar(select(func.max(SentinelScan.id)).where(SentinelScan.scan_complete.is_(True)))
    if latest_id is None:
        return []
    q = (
        select(SentinelRoadRisk, Road.road_name, Road.road_number)
        .join(Road, SentinelRoadRisk.road_id == Road.id)
        .where(SentinelRoadRisk.scan_id == latest_id)
        .order_by(SentinelRoadRisk.risk_score.desc().nulls_last())
        .limit(limit)
    )
    rows = db.execute(q).all()
    out = []
    for r, rname, rnum in rows:
        out.append(
            {
                "road_id": r.road_id,
                "road_name": rname,
                "road_number": rnum,
                "risk_score": float(r.risk_score) if r.risk_score is not None else None,
                "risk_level": r.risk_level,
                "convergence_count": r.convergence_count,
                "primary_driver": r.primary_driver,
                "recommendation": r.recommendation,
            }
        )
    return out


def get_latest_scan_summary(db: Session) -> dict[str, Any] | None:
    scan = db.execute(select(SentinelScan).order_by(SentinelScan.id.desc()).limit(1)).scalar_one_or_none()
    if scan is None:
        return None
    return {
        "scan_id": scan.id,
        "scan_time": scan.scan_time.isoformat() if scan.scan_time else None,
        "red_flag_active": scan.red_flag_active,
        "atmosphere_fwi": float(scan.atmosphere_fwi) if scan.atmosphere_fwi is not None else None,
        "road_count": scan.road_count,
        "scan_complete": scan.scan_complete,
    }


def list_road_risks_for_latest_scan(
    db: Session,
    *,
    level: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    latest_id = db.scalar(select(func.max(SentinelScan.id)).where(SentinelScan.scan_complete.is_(True)))
    if latest_id is None:
        return []
    q = (
        select(SentinelRoadRisk, Road.road_name)
        .join(Road, SentinelRoadRisk.road_id == Road.id)
        .where(SentinelRoadRisk.scan_id == latest_id)
    )
    if level:
        q = q.where(SentinelRoadRisk.risk_level == level.strip().lower())
    q = q.order_by(SentinelRoadRisk.risk_score.desc().nulls_last()).limit(min(limit, 500))
    rows = db.execute(q).all()
    out = []
    for r, rname in rows:
        out.append(
            {
                "road_id": r.road_id,
                "road_name": rname,
                "risk_score": float(r.risk_score) if r.risk_score is not None else None,
                "risk_level": r.risk_level,
                "convergence_count": r.convergence_count,
                "primary_driver": r.primary_driver,
                "recommendation": r.recommendation,
                "atmosphere_contributing": r.atmosphere_contributing,
                "canopy_contributing": r.canopy_contributing,
                "ground_contributing": r.ground_contributing,
            }
        )
    return out


def get_road_risk_breakdown(db: Session, road_id: int) -> dict[str, Any] | None:
    scan = db.execute(select(SentinelScan).order_by(SentinelScan.id.desc()).limit(1)).scalar_one_or_none()
    if scan is None:
        return None
    rr = db.execute(
        select(SentinelRoadRisk).where(
            SentinelRoadRisk.scan_id == scan.id,
            SentinelRoadRisk.road_id == road_id,
        )
    ).scalar_one_or_none()
    if rr is None:
        return None
    atmos = fetch_atmosphere_signal()
    ground = fetch_ground_signal()
    c_rows = fetch_canopy_signal(db)
    canopy = next((x for x in c_rows if x["road_id"] == road_id), {})
    return {
        "scan_id": scan.id,
        "scan_time": scan.scan_time.isoformat() if scan.scan_time else None,
        "road_id": road_id,
        "risk": {
            "risk_score": float(rr.risk_score) if rr.risk_score is not None else None,
            "risk_level": rr.risk_level,
            "convergence_count": rr.convergence_count,
            "primary_driver": rr.primary_driver,
            "recommendation": rr.recommendation,
            "atmosphere_contributing": rr.atmosphere_contributing,
            "canopy_contributing": rr.canopy_contributing,
            "ground_contributing": rr.ground_contributing,
        },
        "streams": {
            "atmosphere": atmos,
            "canopy": canopy,
            "ground": ground,
        },
    }


def get_road_risk_history(db: Session, road_id: int, max_scans: int = 30) -> list[dict[str, Any]]:
    q = (
        select(SentinelRoadRisk, SentinelScan.scan_time)
        .join(SentinelScan, SentinelRoadRisk.scan_id == SentinelScan.id)
        .where(SentinelRoadRisk.road_id == road_id)
        .where(SentinelScan.scan_complete.is_(True))
        .order_by(SentinelScan.scan_time.desc())
        .limit(max_scans)
    )
    rows = db.execute(q).all()
    return [
        {
            "scan_id": r.scan_id,
            "scan_time": st.isoformat() if st else None,
            "risk_score": float(r.risk_score) if r.risk_score is not None else None,
            "risk_level": r.risk_level,
            "convergence_count": r.convergence_count,
        }
        for r, st in rows
    ]


def scheduled_scan_job() -> None:
    """Background job: open a DB session and run one scan."""
    if get_settings().testing or not get_settings().sentinel_scheduler_enabled:
        return
    from backend.database import get_session_factory

    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        run_convergence_scan(db)
    except Exception:
        logger.exception("sentinel scheduled scan failed")
        db.rollback()
    finally:
        db.close()


def red_flag_check_job() -> None:
    if get_settings().testing or not get_settings().sentinel_scheduler_enabled:
        return
    try:
        s = fetch_atmosphere_signal()
        if s.get("red_flag_active"):
            scheduled_scan_job()
    except Exception:
        logger.exception("sentinel red-flag check failed")
