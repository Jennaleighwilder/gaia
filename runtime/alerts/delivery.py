"""
GAIA Alert Delivery — unified output layer.

Writes to file, webhook, SMS (Twilio), email (SMTP).
Each channel enabled via env vars. File is always on.
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
ALERTS_DIR = ROOT / "runs" / "alerts"


class AlertDelivery:
    """Deliver alerts to configured channels: file, webhook, SMS, email."""

    def send(self, alert: dict) -> list[str]:
        methods = []

        self._write_to_file(alert)
        methods.append("file")

        webhook_url = os.environ.get("GAIA_WEBHOOK_URL")
        if webhook_url:
            if self._post_webhook(alert, webhook_url):
                methods.append("webhook")

        twilio_keys = [
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_FROM",
            "GAIA_ALERT_PHONE",
        ]
        if all(os.environ.get(k) for k in twilio_keys):
            if self._send_sms(alert):
                methods.append("sms")

        if os.environ.get("GAIA_ALERT_EMAIL"):
            if self._send_email(alert):
                methods.append("email")

        return methods

    def _write_to_file(self, alert: dict) -> Path:
        ALERTS_DIR.mkdir(parents=True, exist_ok=True)
        date_dir = ALERTS_DIR / datetime.now(timezone.utc).strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        aid = alert.get("alert_id", "unknown")
        path = date_dir / f"{aid}.json"
        path.write_text(json.dumps(alert, indent=2) + "\n")
        return path

    def _post_webhook(self, alert: dict, url: str) -> bool:
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

    def _send_sms(self, alert: dict) -> bool:
        try:
            from twilio.rest import Client

            client = Client(
                os.environ["TWILIO_ACCOUNT_SID"],
                os.environ["TWILIO_AUTH_TOKEN"],
            )
            body = self.format_sms(alert)
            client.messages.create(
                to=os.environ["GAIA_ALERT_PHONE"],
                from_=os.environ["TWILIO_FROM"],
                body=body[:160],
            )
            return True
        except ImportError:
            logger.warning("twilio not installed: pip install twilio")
            return False
        except Exception as e:
            logger.warning("SMS send failed: %s", e)
            return False

    def _send_email(self, alert: dict) -> bool:
        if not all(
            os.environ.get(k)
            for k in ("GAIA_SMTP_HOST", "GAIA_SMTP_USER", "GAIA_SMTP_PASS")
        ):
            return False
        try:
            subject, body = self.format_email(alert)
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))
            with smtplib.SMTP(
                os.environ["GAIA_SMTP_HOST"],
                int(os.environ.get("GAIA_SMTP_PORT", "587")),
            ) as s:
                s.starttls()
                s.login(os.environ["GAIA_SMTP_USER"], os.environ["GAIA_SMTP_PASS"])
                s.sendmail(
                    os.environ["GAIA_SMTP_USER"],
                    os.environ["GAIA_ALERT_EMAIL"],
                    msg.as_string(),
                )
            return True
        except Exception as e:
            logger.warning("Email send failed: %s", e)
            return False

    def format_sms(self, alert: dict) -> str:
        """Keep under 160 chars. Uses canonical format from alert_formatter."""
        from runtime.alerts.alert_formatter import format_alert_sms
        return format_alert_sms(alert)

    def format_email(self, alert: dict) -> tuple[str, str]:
        subject = (
            f"GAIA {alert.get('severity', 'ALERT')}: "
            f"{alert.get('alert_type', 'ALERT')} — "
            f"{str(alert.get('county', '') or (alert.get('counties') or [''])[0]).upper()} TN"
        )
        body = self._render_alert_html(alert)
        return subject, body

    def _render_alert_html(self, alert: dict) -> str:
        county = alert.get("county", "") or (alert.get("counties", [""]) or [""])[0]
        severity = alert.get("severity", "ALERT")
        alert_type = alert.get("alert_type", "ALERT")
        issued = alert.get("issued", "")
        lead = alert.get("lead_time_minutes", "?")
        signals = alert.get("primary_signals", [])
        signals_html = "".join(f"<li>{s}</li>" for s in signals) if signals else "<li>—</li>"
        return f"""
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; max-width: 600px;">
  <h2>GAIA {severity}: {alert_type}</h2>
  <p><b>County:</b> {county.upper()}, TN</p>
  <p><b>Issued:</b> {issued}</p>
  <p><b>Lead time:</b> {lead} min</p>
  <h3>Primary signals</h3>
  <ul>{signals_html}</ul>
  <p><a href="https://theforgottencode.com/gaia">View status</a></p>
</body>
</html>
"""
