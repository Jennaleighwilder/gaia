"""
GAIA Alert Formatter — human-readable alerts from internal decisions.

Converts governor output to structured alerts for emergency managers,
first responders, and the public.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import Any

# Holston Army Ammunition Plant — known major facility (Hawkins Co)
HOLSTON_AAP = {
    "name": "Holston Army Ammunition Plant",
    "county": "hawkins",
    "chemicals": ["Nitrate compounds", "Toluene"],
    "quantity_lbs": 4600000,
}


def _alert_id(region: str, alert_type: str, seq: int = 0) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
    return f"GAIA-{ts}-{region}-{seq:03d}"


def format_severe_weather_alert(
    region: str,
    decision: str,
    timestamp: str,
    engine_scores: dict,
    engine_details: dict,
    tri_facilities: list[dict],
    hazmat_elevated: bool,
    confidence: float,
    tier1_agreement: int,
    lead_time_minutes: int | None = None,
) -> dict:
    """Format SEVERE WEATHER ALERT."""
    scores = engine_scores or {}
    details = engine_details or {}
    primary_signals = []
    if (s := scores.get("shear")) and s >= 0.6:
        primary_signals.append(f"Shear engine: {s:.2f}")
    rad = details.get("radar", {})
    if rad:
        rot = rad.get("rotation_score", 0)
        if rot > 0.7:
            primary_signals.append("Radar rotation: tornado-indicated")
        elif rot > 0.5:
            primary_signals.append("Radar rotation: moderate")
    goes = details.get("goes", {})
    if goes and goes.get("tpw_mm"):
        primary_signals.append(f"GOES TPW: {goes['tpw_mm']}mm (elevated)")
    hazmat_list = []
    for f in (tri_facilities or [])[:5]:
        hazmat_list.append({
            "name": f.get("name", "Unknown"),
            "county": f.get("county", ""),
            "distance_miles": f.get("distance_miles"),
            "chemicals": f.get("top_chemicals_note", "").split(", ") if f.get("top_chemicals_note") else [],
            "risk": "Class 1 within 5 mi — chemical release risk" if f.get("has_class1") else "within 10 mi",
        })
    terrain_detail = details.get("terrain", {})
    terrain_notes = (
        "NE-SW ridges will enhance rainfall on windward slopes. "
        "Sevier/Blount valley floors at elevated flood risk."
        if terrain_detail.get("valley_flood_risk", 0) > 0.5
        else None
    )
    soil_detail = details.get("soil", {})
    soil_note = None
    if soil_detail.get("soil_moisture") is not None:
        pct = int(soil_detail["soil_moisture"] * 100)
        soil_note = f"Soil saturation {pct}% — runoff will be rapid. Flash flooding possible in narrow valleys."
    issued = timestamp or datetime.now(timezone.utc).isoformat()
    expires_dt = datetime.fromisoformat(issued.replace("Z", "+00:00")) + timedelta(hours=2)
    return {
        "alert_id": _alert_id(region, "SEVERE"),
        "issued": issued,
        "alert_type": "THUNDERSTORM_WARNING" if decision == "WARNING" else "TORNADO_WARNING" if decision == "EMERGENCY" else "SEVERE_WEATHER_WATCH",
        "severity": decision,
        "counties": [region],
        "lead_time_minutes": lead_time_minutes,
        "expires": expires_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "primary_signals": primary_signals,
        "hazmat_facilities": hazmat_list,
        "terrain_notes": terrain_notes,
        "soil_note": soil_note,
        "confidence": round(confidence, 2),
        "tier1_agreement": tier1_agreement,
        "false_alarm_rate_historical": "29.4%",
    }


def format_flash_flood_alert(
    region: str,
    timestamp: str,
    engine_details: dict,
    trigger: str | None = None,
) -> dict:
    """Format FLASH FLOOD WARNING."""
    ff = engine_details.get("flash_flood") or {}
    soil_pct = int((ff.get("soil_moisture") or 0) * 100)
    return {
        "alert_id": _alert_id(region, "FF"),
        "issued": timestamp or datetime.now(timezone.utc).isoformat(),
        "alert_type": "FLASH_FLOOD_WARNING",
        "counties": [region],
        "trigger": trigger or "Terrain-driven flood genesis — saturated soil + valley concentration",
        "soil_saturation": f"{soil_pct}%",
        "valley_risk_counties": [region] if ff.get("valley_risk", 0) > 0.6 else [],
        "time_to_flood_stage": "estimated 45 minutes",
        "reasons": ff.get("reasons", []),
    }


def format_hazmat_advisory(
    facility: dict,
    weather_threat: str,
    county: str,
) -> dict:
    """Format HAZMAT WEATHER ADVISORY (e.g. Holston AAP)."""
    return {
        "alert_id": _alert_id(county, "HAZMAT"),
        "issued": datetime.now(timezone.utc).isoformat(),
        "alert_type": "HAZMAT_WEATHER_ADVISORY",
        "facility": facility.get("name", "Unknown facility"),
        "county": county,
        "weather_threat": weather_threat,
        "chemicals_at_risk": facility.get("chemicals", []),
        "quantity_lbs": facility.get("quantity_lbs"),
        "recommended_action": "Emergency services pre-position",
    }


def format_alert_sms(alert: dict) -> str:
    """
    Format alert for SMS (≤160 chars). Used by Twilio when credentials are set.
    Format:
      GAIA ALERT: [TYPE] [COUNTY] TN
      Lead: [X] min | [HAZMAT: Facility X.Xmi if applicable]
      theforgottencode.com
    """
    alert_type = alert.get("alert_type", "ALERT")
    county = (alert.get("counties") or [alert.get("county", "") or alert.get("region", "")])[0]
    county = str(county).upper() if county else "UNKNOWN"
    lead = alert.get("lead_time_minutes")
    lead_str = str(int(lead)) if lead is not None else "?"
    hazmat_parts = []
    for f in (alert.get("hazmat_facilities") or [])[:1]:
        name = (f.get("name") or "Facility").split(",")[0].strip()
        if len(name) > 12:
            name = name[:10] + ".."
        dist = f.get("distance_miles")
        dist_str = f"{dist:.1f}" if dist is not None else "?"
        hazmat_parts.append(f"HAZMAT: {name} {dist_str}mi")
    hazmat = hazmat_parts[0] if hazmat_parts else ""
    if hazmat:
        line2 = f"Lead: {lead_str} min | {hazmat}"
    else:
        line2 = f"Lead: {lead_str} min"
    type_short = (
        "TORNADO WARNING" if "TORNADO" in alert_type.upper()
        else "THUNDERSTORM WARNING" if "THUNDERSTORM" in alert_type.upper()
        else "SEVERE WATCH" if "WATCH" in alert_type.upper() or "SEVERE" in alert_type.upper()
        else "FLASH FLOOD" if "FLOOD" in alert_type.upper()
        else "HAZMAT ADVISORY" if "HAZMAT" in alert_type.upper()
        else alert_type.replace("_", " ")[:20]
    )
    msg = f"GAIA ALERT: {type_short} {county} TN\n{line2}\ntheforgottencode.com"
    return msg[:160]


def format_from_governor_result(result: dict) -> list[dict]:
    """Convert governor compute_decision_for_payload result to alert list."""
    alerts = []
    region = result.get("region", "unknown")
    decision = result.get("decision", "CLEAR")
    timestamp = result.get("timestamp", "")
    engine_scores = result.get("engine_scores", {})
    engine_details = result.get("engine_details", {})
    tri_facilities = result.get("tri_facilities", [])
    hazmat_elevated = result.get("hazmat_elevated", False)
    confidence = result.get("confidence", 0.0)
    tier1_scores = [float(engine_scores.get(k) or 0) for k in ("goes", "radar", "lightning", "terrain", "soil")]
    tier1_agreement = sum(1 for s in tier1_scores if s > 0.6)
    if decision in ("WARNING", "EMERGENCY"):
        alerts.append(format_severe_weather_alert(
            region=region,
            decision=decision,
            timestamp=timestamp,
            engine_scores=engine_scores,
            engine_details=engine_details,
            tri_facilities=tri_facilities,
            hazmat_elevated=hazmat_elevated,
            confidence=confidence,
            tier1_agreement=tier1_agreement,
        ))
    if result.get("flash_flood_warning"):
        alerts.append(format_flash_flood_alert(region, timestamp, engine_details))
    if hazmat_elevated and tri_facilities:
        class1 = next((f for f in tri_facilities if f.get("has_class1") and f.get("distance_miles", 99) <= 5), None)
        if class1:
            advis = format_hazmat_advisory(
                facility={**class1, "chemicals": class1.get("top_chemicals_note", "").split(", ") if class1.get("top_chemicals_note") else []},
                weather_threat=decision,
                county=region,
            )
            if "Holston" in (class1.get("name") or ""):
                advis["facility"] = HOLSTON_AAP["name"]
                advis["chemicals_at_risk"] = HOLSTON_AAP["chemicals"]
                advis["quantity_lbs"] = HOLSTON_AAP["quantity_lbs"]
            alerts.append(advis)
    return alerts
