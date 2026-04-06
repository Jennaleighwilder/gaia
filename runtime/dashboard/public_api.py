"""
Public API for GitHub Pages + Railway: CORS, NWS proxy, /api/bundle, alert signups.

Wire into Flask in app.py (Part 2): register_public_routes(app)
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
DECISIONS_DB = ROOT / "runs" / "gaia_decisions.db"
RUNS = ROOT / "runs"
HOLLER_SIREN_V5_WESTERN = ROOT / "data" / "holler_siren" / "tfi_v5_western_nc.json"
HOLLER_SIREN_DIR = ROOT / "data" / "holler_siren"
FIRE_DIR = ROOT / "data" / "fire"

try:
    from scripts.holler_siren.gaia_integration import format_alert, holler_siren_alert, load_all_tfi_regions
except Exception:  # pragma: no cover - keep dashboard alive if Holler Siren assets missing
    format_alert = None
    holler_siren_alert = None
    load_all_tfi_regions = None

try:
    from scripts.holler_siren.live_rainfall import get_current_rainfall_noaa
except Exception:  # pragma: no cover - keep dashboard alive if live rainfall helper missing
    get_current_rainfall_noaa = None

NWS_USER_AGENT = os.environ.get(
    "GAIA_NWS_USER_AGENT",
    "(GAIA Weather Intelligence, theforgottencode780@gmail.com)",
)

DEFAULT_CORS = (
    "https://jennaleighwilder.github.io,"
    "https://web-production-ce417.up.railway.app,"
    "https://gaia-api-cfxi.onrender.com,"
    "http://127.0.0.1:5500,"
    "http://localhost:5001"
)


def _cors_origins() -> list[str]:
    raw = os.environ.get("GAIA_CORS_ORIGINS", DEFAULT_CORS)
    return [o.strip() for o in raw.split(",") if o.strip()]


def _apply_cors(response, request_origin: str | None):
    allowed = _cors_origins()
    if request_origin and request_origin in allowed:
        response.headers["Access-Control-Allow-Origin"] = request_origin
    elif "*" in allowed:
        response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response


def _http_get_json(url: str, timeout: int = 25) -> dict | list:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": NWS_USER_AGENT, "Accept": "application/geo+json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def _safe_read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("read json %s: %s", path, e)
        return None


def _safe_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _surface_max_precip_mm_hr(surface: dict | None) -> float | None:
    if not isinstance(surface, dict):
        return None
    stations = surface.get("stations")
    if not isinstance(stations, list):
        return None
    vals = []
    for station in stations:
        if not isinstance(station, dict):
            continue
        val = _safe_float(station.get("precip_1h"))
        if val is not None:
            vals.append(val * 25.4)
    return max(vals) if vals else None


def _gaia_calls() -> dict:
    """Recent WARNING/EMERGENCY rows from decisions DB for banner + strip."""
    out: dict = {"banner": None, "strip": [], "counties": {}}
    if not DECISIONS_DB.exists():
        return out
    try:
        conn = sqlite3.connect(str(DECISIONS_DB))
        rows = conn.execute(
            """
            SELECT county, decision, confidence, timestamp FROM decisions
            WHERE decision IN ('WARNING', 'EMERGENCY')
            ORDER BY id DESC
            LIMIT 30
            """
        ).fetchall()
        conn.close()
    except Exception as e:
        logger.warning("gaia_calls db: %s", e)
        return out

    strip = []
    for county, decision, conf, ts in rows:
        strip.append(
            {
                "county": county,
                "decision": decision,
                "confidence": conf,
                "timestamp": ts,
            }
        )
    out["strip"] = strip[:12]
    out["counties"] = {r[0]: {"decision": r[1], "confidence": r[2], "timestamp": r[3]} for r in rows[:20]}
    if strip:
        top = strip[0]
        out["banner"] = {
            "headline": f"GAIA {top['decision']} — {top['county'].replace('_', ' ').title()}",
            "sub": f"Confidence {top.get('confidence') or 0:.2f} · {top.get('timestamp') or ''}",
        }
    return out


def _safe_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _latest_kpah_scan() -> dict:
    try:
        from runtime.data.nexrad_fetch import _list_nexrad_files
    except Exception as e:
        return {"station": "KPAH", "scan_time": None, "file_key": None, "error": str(e)}

    now = datetime.now(timezone.utc)
    keys = _list_nexrad_files("KPAH", now)
    if not keys:
        keys = _list_nexrad_files("KPAH", now - timedelta(days=1))
    if not keys:
        return {"station": "KPAH", "scan_time": None, "file_key": None}

    key = keys[0]
    match = re.search(r"(K[A-Z0-9]{3})(\d{8})_(\d{6})", key)
    scan_time = None
    if match:
        try:
            scan_time = datetime.strptime(
                match.group(2) + match.group(3), "%Y%m%d%H%M%S"
            ).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            scan_time = None
    return {"station": "KPAH", "scan_time": scan_time, "file_key": key}


def _cells_monitored() -> int:
    if load_all_tfi_regions:
        try:
            cells = load_all_tfi_regions()
            if isinstance(cells, list) and cells:
                return len(cells)
        except Exception as e:
            logger.warning("load all tfi regions: %s", e)
    model = _safe_read_json(HOLLER_SIREN_V5_WESTERN)
    cells = model.get("cells") if isinstance(model, dict) else None
    return len(cells) if isinstance(cells, list) else 40453


def _fire_payload() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    firms = _safe_read_json(FIRE_DIR / "firms_results.json") or {}
    wx = _safe_read_json(FIRE_DIR / "current_wx.json") or {}
    overlay = _safe_read_json(FIRE_DIR / "fire_risk_overlay.json") or {}
    spc = _safe_read_json(FIRE_DIR / "spc_fire_outlook.json") or {}
    drought = _safe_read_json(FIRE_DIR / "drought_monitor.json") or {}
    mtbs = _safe_read_json(FIRE_DIR / "mtbs_historical.json") or {}

    active_fires = firms.get("fires") if isinstance(firms.get("fires"), list) else []
    active_fire_count = len(active_fires)
    double_threat_cells = _safe_int(overlay.get("double_threat_cells")) or 0
    rh = _safe_float(wx.get("relative_humidity_pct"))
    wind = _safe_float(wx.get("wind_mph")) or 0.0

    if active_fire_count > 5 or (rh is not None and rh < 20 and wind > 20):
        alert_level = "CRITICAL"
    elif active_fire_count > 0 or (rh is not None and rh < 30 and wind > 15):
        alert_level = "HIGH"
    elif double_threat_cells > 50:
        alert_level = "ELEVATED"
    else:
        alert_level = "WATCH"

    top_double = overlay.get("top_double_threats")
    if not isinstance(top_double, list):
        top_double = [
            cell
            for cell in (overlay.get("cells") or [])
            if isinstance(cell, dict) and cell.get("double_threat")
        ][:20]

    historical_fires = mtbs if isinstance(mtbs, list) else (mtbs.get("fires") if isinstance(mtbs.get("fires"), list) else [])

    return {
        "timestamp": now,
        "firms_fetched": firms.get("fetched"),
        "fire_overlay_computed": overlay.get("computed"),
        "firms_map_key_configured": bool(firms.get("map_key_configured")),
        "firms_ingest_error": firms.get("error"),
        "pilot_area": "Southern Appalachians pilot - Western NC live fire ingest",
        "nifc_context": (
            "NIFC March 2026 flagged the southern Appalachians. "
            "The same Helene slopes now carry landslide memory and added fire fuel."
        ),
        "active_fires": active_fires,
        "active_fire_count": active_fire_count,
        "current_weather": wx,
        "spc_outlook": spc,
        "drought_proxy": drought,
        "historical_fires": historical_fires,
        "historical_fire_count": len(historical_fires),
        "fire_regime_summary": overlay.get("fire_regime_summary") or {},
        "double_threat_cells": double_threat_cells,
        "top_double_threats": top_double[:20],
        "fire_alert_level": alert_level,
    }


def _status_payload() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    tess = _safe_read_json(RUNS / "live_tess.json") or {}
    gaia_calls = _gaia_calls()

    ao_current = _safe_float(((tess.get("layers") or {}).get("transport") or {}).get("ao"))
    if ao_current is None:
        ao_current = _safe_float(tess.get("ao_current"))

    gulf_anomaly = _safe_float(tess.get("gulf_sst_anomaly"))
    if gulf_anomaly is None:
        gulf_anomaly = _safe_float(((tess.get("layers") or {}).get("loading") or {}).get("gulf_sst_anomaly"))

    tess_score = _safe_float(tess.get("tess_score"))
    risk_level = tess.get("risk_level")
    active_calls = len((gaia_calls.get("strip") or []))
    gaia_status = "ACTIVE" if active_calls > 0 or (tess_score is not None and tess_score >= 0.55) else "DORMANT"

    holler_baseline = {
        "alert_level": "—",
        "cells_monitored": _cells_monitored(),
        "pilot_area": "Western NC + expansion regions",
        "timestamp": now,
    }
    if holler_siren_alert:
        try:
            baseline = holler_siren_alert(rainfall_mm_hr=0.0, antecedent_sat_pct=0.0)
            holler_baseline.update(
                {
                    "alert_level": baseline.get("alert_level", "—"),
                    "pilot_area": baseline.get("pilot_area", holler_baseline["pilot_area"]),
                    "timestamp": baseline.get("timestamp", now),
                }
            )
        except Exception as e:
            holler_baseline["error"] = str(e)

    radar_status = _latest_kpah_scan()
    return {
        "gaia_status": gaia_status,
        "gaia_alert_level": risk_level or ("ACTIVE" if active_calls else "DORMANT"),
        "gaia_alert_timestamp": tess.get("timestamp") or now,
        "ao_current": ao_current,
        "gulf_anomaly": gulf_anomaly,
        "holler_siren_baseline": holler_baseline,
        "radar_status": radar_status,
        "last_updated": now,
        "validation": {
            "radar_lead_minutes": 193,
            "holler_siren_auc": 0.842,
            "holler_siren_trained_on": 1804,
            "holler_siren_cells": _cells_monitored(),
            "holler_siren_model": "GradientBoosting",
            "holler_siren_note": "Western NC Helene model with transfer-model expansion into new regions.",
        },
    }


def register_public_routes(app) -> None:
    """Register CORS + public JSON routes on the Flask app."""
    from flask import Response, jsonify, request

    def require_key(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            expected = os.environ.get("API_KEY")
            if not expected:
                return f(*args, **kwargs)
            key = request.headers.get("X-API-Key") or request.args.get("api_key")
            if key != expected:
                return jsonify({"error": "unauthorized"}), 401
            return f(*args, **kwargs)

        return decorated

    @app.before_request
    def _cors_preflight():
        if request.method == "OPTIONS" and request.path.startswith("/api/"):
            r = Response(status=204)
            return _apply_cors(r, request.headers.get("Origin"))

    @app.after_request
    def cors_after(response):
        origin = request.headers.get("Origin")
        return _apply_cors(response, origin)

    @app.route("/api/nws/alerts")
    def api_nws_alerts():
        """Proxy NWS active alerts (browser-safe for GitHub Pages)."""
        q = request.query_string.decode("utf-8") if request.query_string else ""
        base = "https://api.weather.gov/alerts/active"
        url = f"{base}?{q}" if q else f"{base}?status=actual&limit=50"
        try:
            data = _http_get_json(url)
            return jsonify(data)
        except urllib.error.HTTPError as e:
            return jsonify({"error": str(e.code), "detail": e.reason}), 502
        except Exception as e:
            logger.exception("nws proxy")
            return jsonify({"error": "nws_proxy_failed", "detail": str(e)}), 502

    @app.route("/api/nws/obs/<station>")
    def api_nws_obs(station: str):
        """Proxy latest observation for a station ID (e.g. KTYS)."""
        url = f"https://api.weather.gov/stations/{station}/observations/latest"
        try:
            data = _http_get_json(url)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)}), 502

    @app.route("/api/bundle")
    def api_bundle():
        """Single JSON for static dashboard: TESS, surface, soundings, GAIA calls."""
        surface = _safe_read_json(RUNS / "live_surface.json")
        fire_payload = _fire_payload()
        bundle = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tess": _safe_read_json(RUNS / "live_tess.json"),
            "surface": surface,
            "soundings": _safe_read_json(RUNS / "live_soundings.json"),
            "gaia_calls": _gaia_calls(),
            "status": _status_payload(),
            "fire": {
                "alert_level": fire_payload["fire_alert_level"],
                "active_fires": fire_payload["active_fire_count"],
                "double_threat_cells": fire_payload["double_threat_cells"],
            },
        }

        if holler_siren_alert:
            try:
                rainfall_mm_hr = _safe_float(request.args.get("rainfall_mm_hr"))
                if rainfall_mm_hr is None:
                    precip_rate_in_hr = _safe_float(request.args.get("precip_rate_in_hr"))
                    if precip_rate_in_hr is not None:
                        rainfall_mm_hr = precip_rate_in_hr * 25.4
                if rainfall_mm_hr is None:
                    rainfall_mm_hr = _surface_max_precip_mm_hr(surface)
                if rainfall_mm_hr is None and get_current_rainfall_noaa is not None:
                    try:
                        live_rain, live_source = get_current_rainfall_noaa()
                    except Exception as e:
                        logger.warning("get_current_rainfall_noaa in bundle: %s", e)
                        live_rain, live_source = None, None
                    if live_rain is not None:
                        rainfall_mm_hr = live_rain
                        bundle["holler_siren_live"] = {
                            "rainfall_mm_hr": live_rain,
                            "source": live_source,
                        }

                if rainfall_mm_hr is not None:
                    antecedent_sat_pct = _safe_float(request.args.get("antecedent_sat_pct")) or 0.0
                    duration_hr = _safe_float(request.args.get("duration_hr")) or 6.0
                    lat_min = _safe_float(request.args.get("lat_min"))
                    lon_min = _safe_float(request.args.get("lon_min"))
                    lat_max = _safe_float(request.args.get("lat_max"))
                    lon_max = _safe_float(request.args.get("lon_max"))
                    bbox = None
                    if None not in (lat_min, lon_min, lat_max, lon_max):
                        bbox = (lat_min, lon_min, lat_max, lon_max)
                    bundle["holler_siren"] = holler_siren_alert(
                        rainfall_mm_hr=rainfall_mm_hr,
                        bbox=bbox,
                        antecedent_sat_pct=antecedent_sat_pct,
                        duration_hr=duration_hr,
                    )
            except Exception as e:
                logger.exception("holler_siren block in /api/bundle")
                bundle["holler_siren_error"] = str(e)
        return jsonify(bundle)

    @app.route("/api/fire")
    def api_fire():
        """GAIA fire layer - active detections, weather, and terrain overlap."""
        return jsonify(_fire_payload())

    @app.route("/api/status")
    def api_status():
        return jsonify(_status_payload())

    @app.route("/api/holler_siren")
    @require_key
    def api_holler_siren():
        if not holler_siren_alert:
            return jsonify({"error": "holler_siren_unavailable"}), 503

        rainfall = _safe_float(request.args.get("rainfall_mm_hr"))
        if rainfall is None:
            precip_rate = _safe_float(request.args.get("precip_rate_in_hr"))
            if precip_rate is not None:
                rainfall = precip_rate * 25.4
        if rainfall is None:
            return jsonify({"error": "rainfall_mm_hr_required"}), 400

        sat_pct = _safe_float(request.args.get("antecedent_sat_pct")) or 0.0
        duration = _safe_float(request.args.get("duration_hr")) or 6.0
        lat_min = _safe_float(request.args.get("lat_min"))
        lon_min = _safe_float(request.args.get("lon_min"))
        lat_max = _safe_float(request.args.get("lat_max"))
        lon_max = _safe_float(request.args.get("lon_max"))
        bbox = None
        if None not in (lat_min, lon_min, lat_max, lon_max):
            bbox = (lat_min, lon_min, lat_max, lon_max)

        result = holler_siren_alert(
            rainfall_mm_hr=rainfall,
            bbox=bbox,
            antecedent_sat_pct=sat_pct,
            duration_hr=duration,
        )
        return jsonify(result)

    @app.route("/api/holler_siren/live")
    @require_key
    def api_holler_siren_live():
        if not holler_siren_alert or get_current_rainfall_noaa is None:
            return jsonify({"error": "holler_siren_live_unavailable"}), 503

        rain, source = get_current_rainfall_noaa()
        if rain is None:
            rain = 0.0

        sat_pct = _safe_float(request.args.get("antecedent_sat_pct")) or 30.0
        duration = _safe_float(request.args.get("duration_hr")) or 6.0
        lat_min = _safe_float(request.args.get("lat_min"))
        lon_min = _safe_float(request.args.get("lon_min"))
        lat_max = _safe_float(request.args.get("lat_max"))
        lon_max = _safe_float(request.args.get("lon_max"))
        bbox = None
        if None not in (lat_min, lon_min, lat_max, lon_max):
            bbox = (lat_min, lon_min, lat_max, lon_max)

        result = holler_siren_alert(
            rainfall_mm_hr=rain,
            bbox=bbox,
            antecedent_sat_pct=sat_pct,
            duration_hr=duration,
        )
        result["live_rainfall_mm_hr"] = rain
        result["live_data_source"] = source
        return jsonify(result)

    @app.route("/api/holler_siren/alert")
    @require_key
    def api_holler_siren_text_alert():
        if not holler_siren_alert or not format_alert:
            return jsonify({"error": "holler_siren_unavailable"}), 503

        rainfall = _safe_float(request.args.get("rainfall_mm_hr"))
        if rainfall is None:
            precip_rate = _safe_float(request.args.get("precip_rate_in_hr"))
            if precip_rate is not None:
                rainfall = precip_rate * 25.4
        if rainfall is None:
            return jsonify({"error": "rainfall_mm_hr_required"}), 400

        sat_pct = _safe_float(request.args.get("antecedent_sat_pct")) or 0.0
        duration = _safe_float(request.args.get("duration_hr")) or 6.0
        lat_min = _safe_float(request.args.get("lat_min"))
        lon_min = _safe_float(request.args.get("lon_min"))
        lat_max = _safe_float(request.args.get("lat_max"))
        lon_max = _safe_float(request.args.get("lon_max"))
        bbox = None
        if None not in (lat_min, lon_min, lat_max, lon_max):
            bbox = (lat_min, lon_min, lat_max, lon_max)

        result = holler_siren_alert(
            rainfall_mm_hr=rainfall,
            bbox=bbox,
            antecedent_sat_pct=sat_pct,
            duration_hr=duration,
        )
        return format_alert(result), 200, {"Content-Type": "text/plain; charset=utf-8"}

    @app.route("/api/subscribe", methods=["POST"])
    def api_subscribe():
        """Append signup to subscribers.json (SendGrid send happens on GAIA alert — Part 2 wiring)."""
        from runtime.alerts.subscriber_store import append_subscriber

        try:
            data = request.get_json(force=True, silent=False) or {}
        except Exception:
            return jsonify({"ok": False, "error": "invalid_json"}), 400

        email = (data.get("email") or "").strip().lower()
        name = (data.get("name") or "").strip()
        if not email or "@" not in email:
            return jsonify({"ok": False, "error": "email_required"}), 400

        record = {
            "email": email,
            "name": name,
            "zip": (data.get("zip") or "").strip(),
            "city": (data.get("city") or "").strip(),
            "phone": (data.get("phone") or "").strip(),
            "storms": data.get("storms") if isinstance(data.get("storms"), list) else [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            n = append_subscriber(record)
            return jsonify({"ok": True, "total": n})
        except Exception as e:
            logger.exception("subscribe")
            return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    from flask import Flask, jsonify

    app = Flask(__name__)
    register_public_routes(app)

    @app.route("/health")
    def _standalone_health():
        return jsonify(
            {
                "status": "ok",
                "cache_staleness": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    app.run(host="127.0.0.1", port=5001, debug=False)
