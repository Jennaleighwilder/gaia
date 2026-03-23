#!/usr/bin/env python3
"""
Build synthetic radar fixtures from tornado magnitude.
Use when S3 NEXRAD fetch is unreachable — simulates radar catch rate.
EF2+ = strong rotation (tornado_indicated). EF0-EF1 = weak or none.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _magnitude_to_rotation(mag: str) -> float:
    """Plausible rotation couplet (kt) from EF/F rating."""
    if not mag:
        return 35.0
    m = re.match(r"E?F?([0-5])", mag.upper())
    if not m:
        return 35.0
    n = int(m.group(1))
    if n >= 4:
        return 95.0
    if n >= 3:
        return 75.0
    if n >= 2:
        return 60.0
    if n >= 1:
        return 45.0
    return 35.0


def main():
    tornado_path = ROOT / "tests" / "fixtures" / "east_tn_tornado_events.json"
    out_dir = ROOT / "tests" / "fixtures" / "nexrad"
    out_dir.mkdir(parents=True, exist_ok=True)
    events = json.loads(tornado_path.read_text())

    for ev in events:
        mag = ev.get("magnitude", "")
        couplet_kt = _magnitude_to_rotation(mag)
        rot_score = 0.0
        if couplet_kt >= 90:
            rot_score = 1.0
        elif couplet_kt >= 50:
            rot_score = 0.7 + 0.3 * (couplet_kt - 50) / 40
        elif couplet_kt >= 30:
            rot_score = 0.5 + 0.2 * (couplet_kt - 30) / 20
        else:
            rot_score = 0.3 * (couplet_kt / 30)

        refl = 55 if "2" in mag or "3" in mag or "4" in mag or "5" in mag else 45
        result = {
            "event_id": ev["event_id"],
            "date": ev["date"],
            "event_datetime_utc": ev.get("event_datetime_utc", ""),
            "magnitude": mag,
            "county": ev.get("county", ""),
            "station": "KMRX",
            "composite_reflectivity": refl,
            "velocity_max": couplet_kt / 2,
            "velocity_min": -couplet_kt / 2,
            "rotation_couplet_kt": couplet_kt,
            "rotation_score": round(rot_score, 4),
            "vil": 40 if rot_score > 0.6 else 25,
            "echo_top_km": 12,
            "tornado_indicated": rot_score > 0.7,
            "file_key": "(synthetic)",
        }
        out = out_dir / f"{ev['date']}_{ev['event_id']}_KMRX.json"
        out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Built {len(events)} synthetic radar fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
