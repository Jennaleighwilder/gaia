"""
GAIA Daemon — runs continuously: cache + governor every 5 min.
Writes WARNING+ to runs/alerts/, dispatches webhook/SMS, logs to SQLite.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

EAST_TN_COUNTIES = [
    "knox", "sevier", "blount", "greene", "hamblen",
    "hawkins", "washington", "grainger", "sullivan", "anderson",
]


def main():
    from runtime.cache.data_cache import GAIADataCache
    from runtime.governor.governor import compute_decision_for_payload, reset_runtime_state
    from runtime.alerts.alert_formatter import format_from_governor_result
    from runtime.alerts.alert_dispatcher import dispatch
    from runtime.monitor.health import run_and_alert

    cache = GAIADataCache()
    cache.start()

    alerts_dir = ROOT / "runs" / "alerts"
    alerts_dir.mkdir(parents=True, exist_ok=True)
    db_path = ROOT / "runs" / "gaia_decisions.db"

    def init_db():
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                county TEXT,
                decision TEXT,
                confidence REAL,
                alert_json TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    init_db()

    # Upper-air sounding state
    _sounding_data = None
    _sounding_fetched_hour = -1

    def _refresh_soundings():
        nonlocal _sounding_data, _sounding_fetched_hour
        now = datetime.now(timezone.utc)
        target_hour = 12 if now.hour >= 9 else 0
        if _sounding_fetched_hour == target_hour and _sounding_data is not None:
            return
        try:
            from runtime.data.sounding_client import fetch_all_soundings
            _sounding_data = fetch_all_soundings()
            _sounding_fetched_hour = target_hour
            risk = _sounding_data.get("sounding_risk", "?")
            n = _sounding_data.get("station_count", 0)
            stp = _sounding_data.get("regional_max_stp", 0)
            logger.info("Soundings refreshed: %d stations | STP %.2f | Risk %s", n, stp, risk)
        except Exception as e:
            logger.warning("Sounding fetch failed (will retry): %s", e)

    def _best_upper_air() -> dict | None:
        if not _sounding_data or not _sounding_data.get("stations"):
            return None
        best = max(_sounding_data["stations"],
                    key=lambda s: s.get("significant_tornado_parameter", 0))
        return best

    interval_sec = 300
    logger.info("GAIA daemon started. Evaluating %d counties every %d sec", len(EAST_TN_COUNTIES), interval_sec)

    while True:
        try:
            run_and_alert(cache)
            reset_runtime_state()
            _refresh_soundings()
            upper_air = _best_upper_air()
            for county in EAST_TN_COUNTIES:
                payload = {
                    "region": county,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "station_observations": [],
                    "expected_station_ids": [],
                    "environmental_context": {},
                    "upper_air": upper_air,
                    "_from_cache": cache,
                }
                result = compute_decision_for_payload(payload)
                decision = result.get("decision", "CLEAR")
                confidence = result.get("confidence", 0.0)

                conn = sqlite3.connect(db_path)
                conn.execute(
                    "INSERT INTO decisions (timestamp, county, decision, confidence, alert_json, created_at) VALUES (?,?,?,?,?,?)",
                    (
                        result.get("timestamp"),
                        county,
                        decision,
                        confidence,
                        json.dumps(result) if result else None,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
                conn.close()

                if decision in ("WARNING", "EMERGENCY") or result.get("flash_flood_warning") or result.get("wildfire_warning"):
                    alerts = format_from_governor_result(result)
                    if alerts:
                        dispatch(alerts)
                        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                        day_dir = alerts_dir / today
                        day_dir.mkdir(parents=True, exist_ok=True)
                        for i, a in enumerate(alerts):
                            fpath = day_dir / f"{a.get('alert_id', 'alert')}-{i}.json"
                            fpath.write_text(json.dumps(a, indent=2) + "\n")
                        logger.info("Alerts issued for %s: %s", county, [a.get("alert_type") for a in alerts])

        except Exception as e:
            logger.exception("Daemon cycle failed: %s", e)

        time.sleep(interval_sec)


def status_only() -> None:
    """Report daemon status, counties, latest decisions, cache status."""
    import subprocess
    db_path = ROOT / "runs" / "gaia_decisions.db"
    print("=== GAIA Status ===\n")
    try:
        out = subprocess.run(
            ["ps", "aux"],
            capture_output=True, text=True, timeout=5,
        )
        running = "gaia_daemon" in (out.stdout or out.stderr or "")
    except Exception:
        running = False
    print(f"Daemon running: {'Yes' if running else 'No'}")
    print(f"Counties: {', '.join(EAST_TN_COUNTIES)}")
    print()
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cur = conn.execute(
            "SELECT county, decision, confidence, timestamp FROM decisions ORDER BY id DESC LIMIT 20"
        )
        rows = cur.fetchall()
        conn.close()
        print("Latest decisions (last 20):")
        for county, dec, conf, ts in rows:
            print(f"  {county}: {dec} (conf={conf:.2f}) @ {ts or ''}")
    else:
        print("No decisions database yet.")
    print()
    try:
        from runtime.cache.data_cache import GAIADataCache
        print("Data cache: GAIADataCache module loaded")
    except Exception as e:
        print(f"Data cache: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--status-only":
        status_only()
    else:
        main()
