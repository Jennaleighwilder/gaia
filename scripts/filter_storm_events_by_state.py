#!/usr/bin/env python3
"""
Filter NOAA Storm Events by state(s). Uses existing noaa_storm_events data.
Output: tests/fixtures/national_storm_events/{STATE}_events.json
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "tests" / "fixtures" / "noaa_storm_events"
OUT_DIR = ROOT / "tests" / "fixtures" / "national_storm_events"

SEVERE_TYPES = {
    "tornado", "thunderstorm wind", "hail", "flash flood",
    "heavy snow", "ice storm", "winter storm", "blizzard",
    "high wind", "flood", "strong wind", "heavy rain",
    "wildfire", "landslide", "hurricane", "tropical storm",
}


def norm(s: str) -> str:
    return (s or "").strip().lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", nargs="+", default=["OK", "CA", "LA", "WA", "CO", "FL", "MO"])
    args = ap.parse_args()
    states = [s.upper()[:2] for s in args.state]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    STATE_ABBR = {
        "oklahoma": "OK", "california": "CA", "louisiana": "LA",
        "washington": "WA", "colorado": "CO", "florida": "FL",
        "missouri": "MO", "kentucky": "KY", "tennessee": "TN",
        "texas": "TX", "arkansas": "AR", "illinois": "IL", "indiana": "IN", "ohio": "OH",
    }
    by_state = {s: [] for s in states}

    for year in range(1996, 2026):
        p = DATA_DIR / f"details_{year}.csv"
        if not p.exists():
            continue
        with open(p, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                state_raw = norm(row.get("STATE", ""))
                state_key = STATE_ABBR.get(state_raw) or (state_raw[:2].upper() if len(state_raw) >= 2 else "")
                if state_key not in by_state:
                    continue
                etype = norm(row.get("EVENT_TYPE", ""))
                if not any(t in etype for t in SEVERE_TYPES):
                    continue
                begin = (row.get("BEGIN_DATE_TIME", "") or "").strip()
                if begin and "-" in begin[:12]:
                    try:
                        from datetime import datetime
                        dt = datetime.strptime(begin[:10].strip(), "%d-%b-%y")
                        date = dt.strftime("%Y-%m-%d")
                    except Exception:
                        date = ""
                else:
                    date = ""
                if not date and row.get("BEGIN_YEARMONTH"):
                    ym, d = row.get("BEGIN_YEARMONTH", ""), row.get("BEGIN_DAY", "1")
                    date = f"{ym[:4]}-{ym[4:6]}-{int(d):02d}" if len(ym) == 6 else ""
                mag = row.get("MAGNITUDE", "")
                if etype == "tornado" and (row.get("TOR_F_SCALE") or "").strip():
                    mag = (row.get("TOR_F_SCALE", "") or "").strip()
                event = {
                    "event_type": etype,
                    "state": state_key,
                    "county": (row.get("CZ_NAME", "") or "").strip(),
                    "date": date,
                    "lat": row.get("BEGIN_LAT", ""),
                    "lon": row.get("BEGIN_LON", ""),
                    "magnitude": mag,
                }
                by_state[state_key].append(event)

    for state_key, events in by_state.items():
        if events:
            out = OUT_DIR / f"{state_key}_events.json"
            out.write_text(json.dumps(events, indent=2))
            print(f"{state_key}: {len(events)} events -> {out}")


if __name__ == "__main__":
    main()
