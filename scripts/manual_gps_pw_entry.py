#!/usr/bin/env python3
"""
Manual GPS-PW fixture entry when network blocks UCAR/Open-Meteo.

Accepts CSV input: date,pw_mm
Writes/merges into tests/fixtures/gps_pw.json

Usage:
  python scripts/manual_gps_pw_entry.py < input.csv
  python scripts/manual_gps_pw_entry.py --dates  # Print dates needed

NASA POWER (no API key): https://power.larc.nasa.gov/data-access-viewer/
Use lat=36.3, lon=-83.9 for East TN center. Parameter: PRECTOT (or precipitable water).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "gps_pw.json"


def get_dates_to_fetch() -> list[str]:
    """All 19 severe event dates + all quiet day dates."""
    dates = set()
    events = json.loads((ROOT / "tests" / "fixtures" / "east_tn_severe_events.json").read_text())
    for e in events:
        dates.add(e["date"])
    for p in (ROOT / "tests" / "fixtures" / "historical_observations").glob("quiet_*.json"):
        parts = p.stem.split("_")
        if len(parts) >= 2 and "-" in parts[1]:
            dates.add(parts[1])
    return sorted(dates)


def main():
    parser = argparse.ArgumentParser(description="Manual GPS-PW entry from CSV")
    parser.add_argument("--dates", action="store_true", help="Print dates needed (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.dates:
        dates = get_dates_to_fetch()
        print("Dates needing GPS-PW (NASA POWER: lat=36.3, lon=-83.9):")
        for d in dates:
            print(d)
        print(f"\nTotal: {len(dates)} dates")
        return

    # Load existing fixture
    fixture = {}
    if FIXTURE_PATH.exists():
        try:
            fixture = json.loads(FIXTURE_PATH.read_text())
        except Exception:
            pass

    reader = csv.reader(sys.stdin)
    count = 0
    for row in reader:
        if len(row) < 2:
            continue
        date_val, pw_val = row[0].strip(), row[1].strip()
        if "-" in date_val:
            try:
                pw = float(pw_val)
            except ValueError:
                continue
            fixture[date_val] = {"P778": pw, "TYS": pw, "TRI": pw, "GKT": pw}
            count += 1
            print(f"  {date_val}: {pw} mm")

    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(fixture, indent=2) + "\n")
    print(f"Wrote {len(fixture)} dates to {FIXTURE_PATH} ({count} new/updated)")


if __name__ == "__main__":
    main()
