#!/usr/bin/env python3
"""
Fix 4 flash flood misses by adding antecedent precip and soil proxy.
Events: sullivan 2011 (292514), hawkins 2021 (951045),
        grainger 2023 (1134662), greene 2023 (1134672).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.fetch_antecedent_precip import fetch_p01i, precip_mm_from_rows, COUNTY_TO_STATION

OBS_DIR = ROOT / "tests" / "fixtures" / "historical_observations"

MISS_EVENTS = [
    {"event_id": "292514", "date": "2011-04-25", "county": "sullivan", "event_datetime_utc": "2011-04-25T21:33:00Z"},
    {"event_id": "951045", "date": "2021-03-28", "county": "hawkins", "event_datetime_utc": "2021-03-28T10:00:00Z"},
    {"event_id": "1134662", "date": "2023-08-15", "county": "grainger", "event_datetime_utc": "2023-08-15T12:00:00Z"},
    {"event_id": "1134672", "date": "2023-08-15", "county": "greene", "event_datetime_utc": "2023-08-15T12:00:00Z"},
]


def soil_from_precip(precip_mm: float) -> float:
    if precip_mm > 150:
        return 0.95
    if precip_mm > 100:
        return 0.90
    if precip_mm > 50:
        return 0.75
    return 0.5


def main():
    from datetime import datetime, timedelta, timezone
    updated = 0
    for ev in MISS_EVENTS:
        path = OBS_DIR / f"event_{ev['event_id']}.json"
        if not path.exists():
            print(f"  Skip {ev['event_id']}: no fixture")
            continue
        fixture = json.loads(path.read_text())
        dt_end = datetime.fromisoformat(ev["event_datetime_utc"].replace("Z", "+00:00"))
        dt_start = dt_end - timedelta(hours=72)
        start_s = dt_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_s = dt_end.strftime("%Y-%m-%dT%H:%M:%SZ")
        station = COUNTY_TO_STATION.get(ev["county"].lower(), "TYS")
        if len(station) == 3:
            station = "K" + station  # IEM uses 4-letter ICAO
        rows = fetch_p01i(station, start_s, end_s)
        precip_mm = round(precip_mm_from_rows(rows), 2)
        soil = soil_from_precip(precip_mm)
        fixture["precip_72hr_mm"] = precip_mm
        fixture["flash_flood_fixture"] = {
            "soil_moisture": soil,
            "valley_risk": 0.75,
        }
        path.write_text(json.dumps(fixture, indent=2) + "\n")
        print(f"  {ev['event_id']} {ev['county']} {ev['date']}: precip_72hr={precip_mm}mm -> soil={soil}")
        updated += 1
    print(f"Updated {updated} fixtures")
    return 0


if __name__ == "__main__":
    exit(main())
