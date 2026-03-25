"""
Public API for GitHub Pages + Railway: CORS, NWS proxy, /api/bundle, alert signups.

Wire into Flask in app.py (Part 2): register_public_routes(app)
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
DECISIONS_DB = ROOT / "runs" / "gaia_decisions.db"
RUNS = ROOT / "runs"

NWS_USER_AGENT = os.environ.get(
    "GAIA_NWS_USER_AGENT",
    "(GAIA Weather Intelligence, theforgottencode780@gmail.com)",
)

DEFAULT_CORS = (
    "https://jennaleighwilder.github.io,"
    "https://gaia-production.up.railway.app,"
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


def register_public_routes(app) -> None:
    """Register CORS + public JSON routes on the Flask app."""
    from flask import Response, jsonify, request

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
        bundle = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tess": _safe_read_json(RUNS / "live_tess.json"),
            "surface": _safe_read_json(RUNS / "live_surface.json"),
            "soundings": _safe_read_json(RUNS / "live_soundings.json"),
            "gaia_calls": _gaia_calls(),
        }
        return jsonify(bundle)

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
