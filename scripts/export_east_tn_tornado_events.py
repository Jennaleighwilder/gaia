#!/usr/bin/env python3
"""
Export tornado events from filtered East TN storm data.
Output: JSON list for ASOS fetch + fixture build.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "tests" / "fixtures" / "noaa_storm_events"
OUT_PATH = ROOT / "tests" / "fixtures" / "east_tn_tornado_events.json"

EAST_TN_COUNTIES = {
    "knox", "sevier", "blount", "greene", "hamblen",
    "hawkins", "washington", "grainger", "sullivan", "anderson",
}

COUNTY_TO_STATION = {
    "knox": "KTYS", "sevier": "KTYS", "blount": "KTYS", "anderson": "KTYS",
    "greene": "KGKT", "hamblen": "KGKT",
    "hawkins": "KTRI", "washington": "KTRI", "grainger": "KTRI", "sullivan": "KTRI",
}


def norm(s: str) -> str:
    return (s or "").strip().lower().replace(" county", "").replace(" co", "").strip()


def parse_begin_datetime_utc(row: dict) -> str | None:
    """Parse BEGIN_DATE_TIME + CZ_TIMEZONE to UTC ISO."""
    dt_str = (row.get("BEGIN_DATE_TIME") or "").strip()
    tz_str = (row.get("CZ_TIMEZONE") or "EST-5").strip()
    if not dt_str:
        return None
    # Parse "31-MAR-25 11:04:00" or "07-AUG-23 18:17:00"
    m = re.match(r"(\d{1,2})-([A-Za-z]{3})-(\d{2,4})\s+(\d{1,2}):(\d{2}):(\d{2})", dt_str)
    if not m:
        return None
    day, mon_abbr, yr = int(m.group(1)), m.group(2), int(m.group(3))
    hr, mn, sec = int(m.group(4)), int(m.group(5)), int(m.group(6))
    year = 2000 + yr if yr < 100 else yr
    mon_map = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
               "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}
    month = mon_map.get(mon_abbr.upper(), 1)
    # East TN is EST/EDT. Add 4 (EDT) or 5 (EST) for UTC
    from datetime import timedelta
    utc_offset = 4 if 3 <= month <= 10 else 5
    dt_local = datetime(year, month, day, hr, mn, sec)
    dt_utc = dt_local + timedelta(hours=utc_offset)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    events = []
    for year in range(1996, 2026):
        p = DATA_DIR / f"details_{year}.csv"
        if not p.exists():
            continue
        with open(p, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if norm(row.get("STATE", "")) != "tennessee":
                    continue
                county = norm(row.get("CZ_NAME", ""))
                if county not in EAST_TN_COUNTIES:
                    continue
                etype = norm(row.get("EVENT_TYPE", ""))
                if "tornado" not in etype:
                    continue
                event_id = (row.get("EVENT_ID") or "").strip()
                if not event_id:
                    continue
                station = COUNTY_TO_STATION.get(county, "KTYS")
                begin_utc = parse_begin_datetime_utc(row)
                if not begin_utc:
                    continue
                mag = (row.get("TOR_F_SCALE") or row.get("MAGNITUDE") or "").strip()
                date_str = begin_utc[:10]
                events.append({
                    "event_id": event_id,
                    "date": date_str,
                    "event_datetime_utc": begin_utc,
                    "county": county,
                    "station": station,
                    "event_type": "tornado",
                    "magnitude": mag or "",
                })
    events.sort(key=lambda e: (e["date"], e["event_id"]))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(events, indent=2) + "\n")
    print(f"Exported {len(events)} tornado events to {OUT_PATH}")


if __name__ == "__main__":
    main()
