#!/usr/bin/env python3
"""
Build synthetic radar fixtures for ALL event types.
Use when S3 NEXRAD fetch is unreachable.

Event type -> radar signature:
  tornado: magnitude-based rotation (EF/F scale)
  thunderstorm_wind: reflectivity by speed (>65kt=55dBZ, >50kt=45dBZ, <50kt=35dBZ)
  flash_flood: high VIL, low rotation
  hail: high VIL scaled to hail size
  winter_storm: low reflectivity, no rotation
  wildfire: no radar signature
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _parse_magnitude(mag: str, event_type: str) -> tuple[float, float, float]:
    """Return (rotation_couplet_kt, composite_reflectivity, vil)."""
    mag = (mag or "").strip().upper()
    if event_type == "tornado":
        m = re.match(r"E?F?([0-5])", mag)
        n = int(m.group(1)) if m else 1
        if n >= 4:
            return 95.0, 65, 55
        if n >= 3:
            return 75.0, 60, 50
        if n >= 2:
            return 60.0, 55, 40
        if n >= 1:
            return 45.0, 45, 30
        return 35.0, 45, 25

    if event_type == "thunderstorm_wind":
        m = re.search(r"(\d+(?:\.\d+)?)\s*(\w*)", mag)
        kt = 35.0
        if m:
            val = float(m.group(1))
            unit = (m.group(2) or "").lower()
            if "kt" in unit or "knot" in unit:
                kt = val
            elif "mph" in unit or not unit:
                kt = val / 1.15078
        if kt >= 65:
            return 25.0, 55, 45
        if kt >= 50:
            return 20.0, 45, 35
        return 15.0, 35, 25

    if event_type == "flash_flood":
        return 10.0, 40, 55

    if event_type == "hail":
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:in|IN)?", mag)
        inch = float(m.group(1)) if m else 1.0
        vil = min(70, 25 + inch * 25)
        refl = min(65, 45 + inch * 5)
        return 20.0, refl, vil

    if event_type in ("winter_storm", "heavy_snow", "ice_storm"):
        return 0.0, 25, 15

    if event_type == "wildfire":
        return 0.0, 5, 0

    return 25.0, 40, 30


def main():
    events_path = ROOT / "tests" / "fixtures" / "east_tn_full_events.json"
    out_dir = ROOT / "tests" / "fixtures" / "nexrad"
    if not events_path.exists():
        print("Run export_east_tn_full_events.py first")
        return 1
    events = json.loads(events_path.read_text())
    out_dir.mkdir(parents=True, exist_ok=True)
    for ev in events:
        couplet, refl, vil = _parse_magnitude(ev.get("magnitude", ""), ev.get("event_type", ""))
        rot_score = 0.0
        if couplet >= 90:
            rot_score = 1.0
        elif couplet >= 50:
            rot_score = 0.7 + 0.3 * (couplet - 50) / 40
        elif couplet >= 30:
            rot_score = 0.5 + 0.2 * (couplet - 30) / 20
        elif couplet > 0:
            rot_score = 0.3 * (couplet / 30)
        result = {
            "event_id": ev["event_id"],
            "date": ev["date"],
            "event_datetime_utc": ev.get("event_datetime_utc", ""),
            "magnitude": ev.get("magnitude", ""),
            "county": ev.get("county", ""),
            "event_type": ev.get("event_type", ""),
            "station": "KMRX",
            "composite_reflectivity": refl,
            "velocity_max": couplet / 2,
            "velocity_min": -couplet / 2,
            "rotation_couplet_kt": couplet,
            "rotation_score": round(rot_score, 4),
            "vil": vil,
            "echo_top_km": 12 if couplet > 20 else 8,
            "tornado_indicated": rot_score > 0.7,
            "file_key": "(synthetic)",
        }
        out = out_dir / f"{ev['date']}_{ev['event_id']}_KMRX.json"
        out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Built {len(events)} synthetic radar fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
