"""
GAIA System Health Monitor — runs every 5 minutes.

Checks: data cache freshness, governor activity, disk space, memory.
On failure: sends SYSTEM_HEALTH_ALERT to delivery channels.
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
DECISIONS_DB = ROOT / "runs" / "gaia_decisions.db"
EVIDENCE_DIR = ROOT / "runs" / "evidence"

# Freshness thresholds (minutes)
GOES_TPW_MAX_AGE_MIN = 15
NEXRAD_MAX_AGE_MIN = 10
USGS_STREAMFLOW_MAX_AGE_MIN = 20
GOVERNOR_MAX_AGE_MIN = 10
DISK_FREE_GB_MIN = 1.0


def run_health_checks(cache: Any | None = None) -> dict[str, Any]:
    """Run all health checks. Returns {ok: bool, checks: {...}, failures: [...]}."""
    failures = []
    checks = {}

    # 1. Data cache feed updates (if cache provided and started)
    if cache is not None:
        try:
            last_fetch = getattr(cache, "get_last_fetch", lambda: {})()
            now = time.time()
            for key, ts in last_fetch.items():
                age_min = (now - ts) / 60 if ts else 999
                checks[f"cache_{key}"] = {"age_min": round(age_min, 1), "stale": age_min > 60}
                if key == "goes_tpw" and age_min > GOES_TPW_MAX_AGE_MIN:
                    failures.append(f"GOES TPW data stale ({age_min:.0f} min old)")
                elif key == "nexrad" and age_min > NEXRAD_MAX_AGE_MIN:
                    failures.append(f"NEXRAD data stale ({age_min:.0f} min old)")
                elif key == "usgs_streamflow" and age_min > USGS_STREAMFLOW_MAX_AGE_MIN:
                    failures.append(f"USGS streamflow stale ({age_min:.0f} min old)")
        except Exception as e:
            failures.append(f"Cache check failed: {e}")
            checks["cache"] = {"error": str(e)}

    # 2. Governor running decisions
    if DECISIONS_DB.exists():
        try:
            conn = sqlite3.connect(str(DECISIONS_DB))
            row = conn.execute(
                "SELECT MAX(created_at) FROM decisions"
            ).fetchone()
            conn.close()
            if row and row[0]:
                last = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                age_min = (datetime.now(timezone.utc) - last).total_seconds() / 60
                checks["governor"] = {"last_decision_age_min": round(age_min, 1)}
                if age_min > GOVERNOR_MAX_AGE_MIN:
                    failures.append(f"Governor idle ({age_min:.0f} min since last decision)")
            else:
                checks["governor"] = {"last_decision": "never"}
        except Exception as e:
            failures.append(f"Governor check failed: {e}")
            checks["governor"] = {"error": str(e)}
    else:
        checks["governor"] = {"status": "no_decisions_db"}

    # 3. Disk space
    try:
        stat = shutil.disk_usage(str(ROOT))
        free_gb = stat.free / (1024**3)
        checks["disk"] = {"free_gb": round(free_gb, 2)}
        if free_gb < DISK_FREE_GB_MIN:
            failures.append(f"Low disk space: {free_gb:.1f} GB free")
    except Exception as e:
        failures.append(f"Disk check failed: {e}")
        checks["disk"] = {"error": str(e)}

    # 4. Memory (evidence files can fill disk)
    try:
        import psutil
        mem = psutil.virtual_memory()
        checks["memory"] = {"percent_used": round(mem.percent, 1), "available_gb": round(mem.available / (1024**3), 2)}
        if mem.percent > 95:
            failures.append(f"High memory usage: {mem.percent}%")
    except ImportError:
        checks["memory"] = {"status": "psutil_not_installed"}
    except Exception as e:
        checks["memory"] = {"error": str(e)}

    # 5. Evidence directory size (can grow unbounded)
    if EVIDENCE_DIR.exists():
        try:
            count = sum(1 for _ in EVIDENCE_DIR.rglob("*.json"))
            checks["evidence"] = {"file_count": count}
            if count > 100_000:
                failures.append(f"Evidence directory very large: {count} files")
        except Exception as e:
            checks["evidence"] = {"error": str(e)}

    return {
        "ok": len(failures) == 0,
        "checks": checks,
        "failures": failures,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def send_health_alert(result: dict) -> None:
    """Send SYSTEM_HEALTH_ALERT to delivery channels."""
    try:
        from runtime.alerts.delivery import AlertDelivery

        alert = {
            "alert_id": f"GAIA-HEALTH-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}",
            "issued": result["timestamp"],
            "alert_type": "SYSTEM_HEALTH_ALERT",
            "severity": "WARNING",
            "county": "",
            "failures": result["failures"],
            "checks": result["checks"],
        }
        delivery = AlertDelivery()
        methods = delivery.send(alert)
        logger.info("System health alert sent via %s", methods)
    except Exception as e:
        logger.warning("Failed to send health alert: %s", e)


def run_and_alert(cache: Any | None = None) -> dict[str, Any]:
    """Run checks; if any fail, send alert. Returns result."""
    result = run_health_checks(cache)
    if not result["ok"]:
        logger.warning("Health check failures: %s", result["failures"])
        send_health_alert(result)
    return result
