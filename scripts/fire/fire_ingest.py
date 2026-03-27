#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._http_fetch import fetch_bytes


OUTPUT_DIR = ROOT / "data" / "fire"
BBOX_WNC = (-84.3, 35.0, -81.8, 36.6)
FIRMS_DATASET = "VIIRS_SNPP_NRT"
FIRMS_LOOKBACK_DAYS = 7
USER_AGENT = os.environ.get(
    "GAIA_FIRE_USER_AGENT",
    "GAIA-Fire/1.0 (theforgottencode780@gmail.com)",
)

SPC_URLS = {
    "day1": "https://mapservices.weather.noaa.gov/vector/rest/services/fire_weather/SPC_firewx/MapServer/1/query",
    "day2": "https://mapservices.weather.noaa.gov/vector/rest/services/fire_weather/SPC_firewx/MapServer/4/query",
}
NWS_URL = "https://api.weather.gov/stations/KAVL/observations/latest"
DROUGHT_URL = (
    "https://usdmdataservices.unl.edu/api/CountyStatistics/"
    "GetDroughtSeverityStatisticsByAreaPercent?"
    "aoi=37199,37121&startdate=2026-01-01&enddate=2026-03-27"
    "&statisticsType=2"
)
MTBS_URL = (
    "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_MTBS_01/MapServer/63/query?"
    "where=1%3D1&geometry=-84.3%2C35.0%2C-81.8%2C36.6"
    "&geometryType=esriGeometryEnvelope"
    "&spatialRel=esriSpatialRelIntersects"
    "&inSR=4269"
    "&outFields=FIRE_ID%2CFIRE_NAME%2CYEAR%2CACRES%2CSTARTMONTH"
    "&returnGeometry=false&f=json"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _request_bytes(url: str, *, accept: str = "*/*", timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _float(value, default=None):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _bbox_contains(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    min_lon, min_lat, max_lon, max_lat = BBOX_WNC
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def _geometry_bbox(geometry: dict | None) -> tuple[float, float, float, float] | None:
    if not isinstance(geometry, dict):
        return None

    coords = []

    def walk(node):
        if isinstance(node, (list, tuple)):
            if len(node) >= 2 and all(isinstance(v, (int, float)) for v in node[:2]):
                coords.append((float(node[0]), float(node[1])))
                return
            for child in node:
                walk(child)

    walk(geometry.get("coordinates"))
    if not coords:
        return None

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return min(lons), min(lats), max(lons), max(lats)


def _bbox_intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    a_min_lon, a_min_lat, a_max_lon, a_max_lat = a
    b_min_lon, b_min_lat, b_max_lon, b_max_lat = b
    return not (
        a_max_lon < b_min_lon
        or b_max_lon < a_min_lon
        or a_max_lat < b_min_lat
        or b_max_lat < a_min_lat
    )


def ingest_firms() -> dict:
    print("=== 1. NASA FIRMS VIIRS ===")
    firms_key = os.environ.get("FIRMS_MAP_KEY")
    bbox_str = ",".join(str(v) for v in BBOX_WNC)
    url = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{urllib.parse.quote(firms_key or 'DEMO_KEY', safe='')}/"
        f"{FIRMS_DATASET}/{bbox_str}/{FIRMS_LOOKBACK_DAYS}"
    )

    result = {
        "source": "NASA FIRMS VIIRS SNPP NRT",
        "dataset": FIRMS_DATASET,
        "bbox": BBOX_WNC,
        "lookback_days": FIRMS_LOOKBACK_DAYS,
        "map_key_configured": bool(firms_key),
        "fetched": _now_iso(),
        "fires": [],
        "count": 0,
        "error": None,
    }

    try:
        content = _request_bytes(url, accept="text/csv").decode("utf-8", errors="replace")
        (OUTPUT_DIR / "firms_viirs_7day.csv").write_text(content, encoding="utf-8")

        reader = csv.DictReader(io.StringIO(content))
        fires = []
        for row in reader:
            lat = _float(row.get("latitude"))
            lon = _float(row.get("longitude"))
            if not _bbox_contains(lat, lon):
                continue
            confidence = str(row.get("confidence", "")).strip().lower()
            if confidence and confidence not in {"h", "n", "high", "nominal"}:
                continue
            fires.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "brightness": _float(row.get("bright_ti4"), _float(row.get("brightness"), 0.0)),
                    "confidence": confidence or "unknown",
                    "acq_date": row.get("acq_date", ""),
                    "acq_time": row.get("acq_time", ""),
                    "frp": _float(row.get("frp"), 0.0),
                    "daynight": row.get("daynight", ""),
                    "satellite": row.get("satellite", ""),
                }
            )

        result["fires"] = fires
        result["count"] = len(fires)
        print(f"Active fire detections in western NC (7 days): {len(fires)}")
        for fire in fires[:5]:
            print(
                f"  ({fire['lat']:.3f}, {fire['lon']:.3f}) "
                f"brightness={fire['brightness']:.0f} frp={fire['frp']:.1f} date={fire['acq_date']}"
            )
    except Exception as exc:
        result["error"] = str(exc)
        print(f"FIRMS fetch failed: {exc}")
        if not firms_key:
            print("  -> FIRMS_MAP_KEY is not configured. Register free at:")
            print("     https://firms.modaps.eosdis.nasa.gov/api/")

    _write_json(OUTPUT_DIR / "firms_results.json", result)
    return result


def ingest_spc() -> dict:
    print("\n=== 2. NOAA SPC Fire Weather Outlook ===")
    bbox = BBOX_WNC
    result = {"bbox": bbox, "fetched": _now_iso(), "days": {}}
    spc_labels = {5: "ELEVATED", 8: "CRITICAL", 10: "EXTREME"}

    for day, url in SPC_URLS.items():
        day_result = {
            "url": url,
            "national_feature_count": 0,
            "western_nc_features": [],
            "western_nc_feature_count": 0,
            "error": None,
        }
        try:
            params = {
                "where": "1=1",
                "geometry": ",".join(str(v) for v in bbox),
                "geometryType": "esriGeometryEnvelope",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "dn,valid,expire,idp_source",
                "returnGeometry": "false",
                "f": "geojson",
            }
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            raw = json.loads(_request_bytes(full_url, accept="application/geo+json").decode("utf-8", errors="replace"))
            _write_json(OUTPUT_DIR / f"spc_{day}.json", raw)

            features = raw.get("features") or []
            day_result["national_feature_count"] = len(features)

            western_nc = []
            for feature in features:
                props = feature.get("properties") or {}
                western_nc.append(
                    {
                        "label": spc_labels.get(props.get("dn"), str(props.get("dn"))),
                        "valid": props.get("valid"),
                        "expire": props.get("expire"),
                        "idp_source": props.get("idp_source"),
                    }
                )

            day_result["western_nc_features"] = western_nc
            day_result["western_nc_feature_count"] = len(western_nc)
            print(f"  {day}: {len(western_nc)} polygons touching western NC")
            for feature in western_nc[:3]:
                print(f"    {feature['label']}: valid {feature['valid']}")
        except Exception as exc:
            day_result["error"] = str(exc)
            print(f"  {day} fetch failed: {exc}")

        result["days"][day] = day_result

    _write_json(OUTPUT_DIR / "spc_fire_outlook.json", result)
    return result


def ingest_nws_conditions() -> dict:
    print("\n=== 3. NWS Asheville Conditions ===")
    result = {
        "station": "KAVL (Asheville)",
        "fetched": _now_iso(),
        "fire_weather_flag": False,
        "error": None,
    }

    try:
        obs = json.loads(_request_bytes(NWS_URL, accept="application/geo+json").decode("utf-8", errors="replace"))
        _write_json(OUTPUT_DIR / "kavl_latest_observation.geojson", obs)

        props = obs.get("properties") or {}
        temp_c = _float(((props.get("temperature") or {}).get("value")))
        rh = _float(((props.get("relativeHumidity") or {}).get("value")))
        wind_ms = _float(((props.get("windSpeed") or {}).get("value")))
        wind_dir = _float(((props.get("windDirection") or {}).get("value")))

        temp_f = round(temp_c * 9 / 5 + 32, 1) if temp_c is not None else None
        wind_unit = ((props.get("windSpeed") or {}).get("unitCode")) or ""
        if wind_ms is not None and wind_unit == "wmoUnit:km_h-1":
            wind_mph = round(wind_ms * 0.621371, 1)
        elif wind_ms is not None:
            wind_mph = round(wind_ms * 2.23694, 1)
        else:
            wind_mph = None
        fire_flag = bool(rh is not None and rh < 25 and wind_mph is not None and wind_mph > 15)

        result.update(
            {
                "temp_f": temp_f,
                "relative_humidity_pct": round(rh, 1) if rh is not None else None,
                "wind_mph": wind_mph,
                "wind_unit": wind_unit,
                "wind_dir_deg": wind_dir,
                "timestamp": props.get("timestamp", ""),
                "text_description": props.get("textDescription", ""),
                "fire_weather_flag": fire_flag,
            }
        )

        if fire_flag:
            print(f"  FIRE WEATHER CONDITIONS: RH={rh:.0f}% Wind={wind_mph:.1f} mph")
        else:
            rh_text = f"{rh:.0f}%" if rh is not None else "n/a"
            wind_text = f"{wind_mph:.1f} mph" if wind_mph is not None else "n/a"
            print(f"  Normal conditions: Temp={temp_f}F RH={rh_text} Wind={wind_text}")
    except Exception as exc:
        result["error"] = str(exc)
        print(f"NWS fetch failed: {exc}")

    _write_json(OUTPUT_DIR / "current_wx.json", result)
    return result


def ingest_drought_proxy() -> dict:
    print("\n=== 4. KBDI Drought Index (proxy) ===")
    result = {
        "source": "US Drought Monitor county statistics proxy",
        "counties": ["37199", "37121"],
        "fetched": _now_iso(),
        "records": [],
        "latest": None,
        "error": None,
    }

    try:
        drought = json.loads(_request_bytes(DROUGHT_URL, accept="application/json").decode("utf-8", errors="replace"))
        result["records"] = drought if isinstance(drought, list) else [drought]
        if result["records"]:
            result["latest"] = max(
                result["records"],
                key=lambda row: row.get("mapDate", "") if isinstance(row, dict) else "",
            )
            print(f"  Latest drought proxy record: {result['latest']}")
    except Exception as exc:
        result["error"] = str(exc)
        print(f"Drought monitor fetch failed: {exc}")

    _write_json(OUTPUT_DIR / "drought_monitor.json", result)
    return result


def ingest_mtbs() -> dict:
    print("\n=== 5. MTBS Historical Burns ===")
    result = {
        "source": "USFS MTBS",
        "bbox": BBOX_WNC,
        "fetched": _now_iso(),
        "fires": [],
        "count": 0,
        "error": None,
    }

    try:
        raw = json.loads(fetch_bytes(MTBS_URL).decode("utf-8", errors="replace"))
        _write_json(OUTPUT_DIR / "mtbs_raw.json", raw)

        fires = []
        for feature in raw.get("features") or []:
            attrs = feature.get("attributes") or {}
            fires.append(
                {
                    "id": attrs.get("FIRE_ID") or "",
                    "name": attrs.get("FIRE_NAME") or "",
                    "year": int(attrs.get("YEAR") or 0),
                    "acres": _float(attrs.get("ACRES"), 0.0),
                    "month": int(attrs.get("STARTMONTH") or 0),
                }
            )

        fires.sort(key=lambda item: (item["year"], item["acres"]), reverse=True)
        result["fires"] = fires
        result["count"] = len(fires)
        print(f"  Historical fires in western NC (MTBS 1984-present): {len(fires)}")
        for fire in fires[:10]:
            print(f"  {fire['year']}: {fire['name']} - {fire['acres']:,.0f} acres")
    except Exception as exc:
        result["error"] = str(exc)
        print(f"MTBS fetch failed: {exc}")

    _write_json(OUTPUT_DIR / "mtbs_historical.json", result)
    return result


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    firms = ingest_firms()
    spc = ingest_spc()
    current_wx = ingest_nws_conditions()
    drought = ingest_drought_proxy()
    mtbs = ingest_mtbs()

    summary = {
        "timestamp": _now_iso(),
        "bbox": BBOX_WNC,
        "firms_active_fire_count": firms.get("count", 0),
        "firms_map_key_configured": firms.get("map_key_configured", False),
        "spc_day1_wnc_features": spc.get("days", {}).get("day1", {}).get("western_nc_feature_count", 0),
        "spc_day2_wnc_features": spc.get("days", {}).get("day2", {}).get("western_nc_feature_count", 0),
        "nws_fire_weather_flag": current_wx.get("fire_weather_flag", False),
        "mtbs_fire_count": mtbs.get("count", 0),
        "drought_latest": drought.get("latest"),
        "errors": {
            "firms": firms.get("error"),
            "spc_day1": spc.get("days", {}).get("day1", {}).get("error"),
            "spc_day2": spc.get("days", {}).get("day2", {}).get("error"),
            "nws": current_wx.get("error"),
            "drought": drought.get("error"),
            "mtbs": mtbs.get("error"),
        },
    }
    _write_json(OUTPUT_DIR / "summary.json", summary)
    print("\n=== Fire data saved to data/fire/ ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
