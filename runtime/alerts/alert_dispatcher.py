"""
GAIA Alert Dispatcher — write, webhook, SMS, SQLite.

Dispatches formatted alerts to outputs.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
ALERTS_DIR = ROOT / "runs" / "alerts"
DB_PATH = ROOT / "runs" / "alerts" / "alerts.db"


def _ensure_dirs():
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    (ALERTS_DIR / datetime.now(timezone.utc).strftime("%Y-%m-%d")).mkdir(parents=True, exist_ok=True)


def _init_db():
    _ensure_dirs()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id TEXT UNIQUE,
            issued TEXT,
            alert_type TEXT,
            region TEXT,
            payload_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def write_alert(alert: dict) -> Path:
    """Write alert JSON to runs/alerts/{date}/."""
    _ensure_dirs()
    date_dir = ALERTS_DIR / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    aid = alert.get("alert_id", "unknown")
    path = date_dir / f"{aid}.json"
    path.write_text(json.dumps(alert, indent=2) + "\n")
    return path


def log_to_sqlite(alert: dict) -> None:
    """Log alert to SQLite."""
    try:
        _init_db()
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute(
            "INSERT OR IGNORE INTO alerts (alert_id, issued, alert_type, region, payload_json) VALUES (?,?,?,?,?)",
            (
                alert.get("alert_id"),
                alert.get("issued"),
                alert.get("alert_type"),
                alert.get("counties", [alert.get("region", "")])[0] if alert.get("counties") else alert.get("region", ""),
                json.dumps(alert),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning("Alert SQLite log failed: %s", e)


def post_webhook(alert: dict) -> bool:
    """POST to GAIA_WEBHOOK_URL if set."""
    url = os.environ.get("GAIA_WEBHOOK_URL")
    if not url:
        return False
    try:
        import urllib.request
        req = urllib.request.Request(
            url,
            data=json.dumps(alert).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception as e:
        logger.warning("Webhook POST failed: %s", e)
        return False


def send_sms(alert: dict) -> bool:
    """Send SMS via Twilio if Twilio env vars set. SMS ≤160 chars."""
    sid = os.environ.get("GAIA_TWILIO_ACCOUNT_SID") or os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("GAIA_TWILIO_AUTH_TOKEN") or os.environ.get("TWILIO_AUTH_TOKEN")
    to = os.environ.get("GAIA_TWILIO_TO") or os.environ.get("GAIA_ALERT_PHONE")
    from_ = os.environ.get("GAIA_TWILIO_FROM") or os.environ.get("TWILIO_FROM")
    if not all([sid, token, to, from_]):
        return False
    try:
        from twilio.rest import Client
        from runtime.alerts.alert_formatter import format_alert_sms
        client = Client(sid, token)
        body = format_alert_sms(alert)
        client.messages.create(to=to, from_=from_, body=body[:160])
        return True
    except ImportError:
        logger.warning("twilio not installed")
        return False
    except Exception as e:
        logger.warning("SMS send failed: %s", e)
        return False


def dispatch(alerts: list[dict]) -> list[Path]:
    """Write, webhook, SMS, SQLite for each alert."""
    paths = []
    for alert in alerts:
        path = write_alert(alert)
        paths.append(path)
        log_to_sqlite(alert)
        post_webhook(alert)
        send_sms(alert)
        try:
            from runtime.alerts.email_subscribers import notify_subscribers as email_notify_subscribers

            email_notify_subscribers(alert)
        except Exception as e:
            logger.warning("Subscriber email notify failed: %s", e)
    return paths
