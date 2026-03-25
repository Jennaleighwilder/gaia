"""
SendGrid: email all subscribers when GAIA dispatches an alert.

Env:
  SENDGRID_API_KEY — required to send
  GAIA_FROM_EMAIL — verified sender in SendGrid (default: theforgottencode780@gmail.com)
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

from runtime.alerts.subscriber_store import load_subscribers


def send_via_sendgrid(to_email: str, subject: str, body: str) -> bool:
    key = os.environ.get("SENDGRID_API_KEY")
    from_email = os.environ.get("GAIA_FROM_EMAIL", "theforgottencode780@gmail.com")
    if not key:
        logger.info("SENDGRID_API_KEY not set; skip email to %s", to_email)
        return False

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 200 <= r.status < 300
    except urllib.error.HTTPError as e:
        logger.warning("SendGrid HTTP %s: %s", e.code, e.read()[:500])
        return False
    except Exception as e:
        logger.warning("SendGrid failed: %s", e)
        return False


def format_alert_email(alert: dict) -> tuple[str, str]:
    """Subject + body for subscriber email."""
    atype = alert.get("alert_type") or "GAIA Alert"
    counties = alert.get("counties") or alert.get("county") or alert.get("region") or "your area"
    if isinstance(counties, list):
        counties = ", ".join(str(c) for c in counties)
    subj = f"GAIA early warning: {atype} — {counties}"
    body = f"""GAIA detected a developing hazard before routine government alerts may be issued.

Type: {atype}
Area: {counties}
Issued: {alert.get('issued', '')}

This is an automated message from GAIA (The Forgotten Code Research Institute).
Manage expectations: verify with local NWS and official sources.

— GAIA
"""
    return subj, body


def notify_subscribers(alert: dict) -> int:
    """Send one email per subscriber. Returns number of successful sends."""
    subs = load_subscribers()
    if not subs:
        return 0
    subj, body = format_alert_email(alert)
    ok = 0
    for row in subs:
        em = (row.get("email") or "").strip()
        if not em:
            continue
        if send_via_sendgrid(em, subj, body):
            ok += 1
    return ok
