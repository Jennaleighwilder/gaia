#!/usr/bin/env python3
"""
Add antecedent precipitation (72hr) to event fixtures.
Pulls ASOS hourly precip for 72 hours before event, sums to precip_72hr_mm.
"""

from __future__ import annotations

import json
import time
import urllib.request
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS_PATH = ROOT / "tests" / "fixtures" / "east_tn_full_events.json"
ASOS_DIR = ROOT / "tests" / "fixtures" / "historical_asos"
OBS_DIR = ROOT / "tests" / "fixtures" / "historical_observations"
BASE_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"

COUNTY_TO_STATION = {
    "knox": "TYS", "sevier": "TYS", "blount": "TYS", "anderson": "TYS",
    "greene": "GKT", "hamblen": "GKT",
    "hawkins": "TRI", "washington": "TRI", "grainger": "TRI", "sullivan": "TRI",
}


def fetch_p01i(station: str, start_utc: str, end_utc: str) -> list[dict]:
    """Fetch p01i (precip) for station between start and end. Returns [{valid, p01i}, ...]."""
    url = (
        f"{BASE_URL}?station={station}&data=p01i"
        f"&sts={start_utc}&ets={end_utc}"
        f"&tz=Etc%2FUTC&format=comma"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode("utf-8", errors="replace")
    except Exception:
        return []
    lines = [ln for ln in text.strip().split("\n") if ln and not ln.startswith("#")]
    if not lines:
        return []
    reader = csv.DictReader(lines)
    return list(reader)


def precip_mm_from_rows(rows: list[dict]) -> float:
    """Sum precip from rows. p01i in inches, convert to mm (25.4). T=trace=0.0001 in."""
    total_in = 0.0
    for r in rows:
        p = r.get("p01i", "M")
        if p == "M" or p == "":
            continue
        if p == "T":
            total_in += 0.0001
        else:
            try:
                total_in += float(p)
            except (ValueError, TypeError):
                pass
    return total_in * 25.4


def main():
    from datetime import datetime, timedelta, timezone
    if not EVENTS_PATH.exists():
        print("Run export_east_tn_full_events.py first")
        return 1
    events = json.loads(EVENTS_PATH.read_text())
    obs_dir = OBS_DIR
    updated = 0
    for ev in events:
        eid = ev["event_id"]
        path = obs_dir / f"event_{eid}.json"
        if not path.exists():
            continue
        fixture = json.loads(path.read_text())
        if "precip_72hr_mm" in fixture:
            continue
        date_str = ev["date"]
        dt_end = datetime.fromisoformat(ev.get("event_datetime_utc", date_str + "T12:00:00Z").replace("Z", "+00:00"))
        dt_start = dt_end - timedelta(hours=72)
        start_s = dt_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_s = dt_end.strftime("%Y-%m-%dT%H:%M:%SZ")
        station = COUNTY_TO_STATION.get(ev.get("county", "").lower(), "TYS")
        rows = fetch_p01i(station, start_s, end_s)
        precip_mm = round(precip_mm_from_rows(rows), 2)
        fixture["precip_72hr_mm"] = precip_mm
        path.write_text(json.dumps(fixture, indent=2) + "\n")
        updated += 1
        if updated % 50 == 0:
            print(f"  Updated {updated} fixtures...")
        time.sleep(0.5)
    print(f"Added precip_72hr_mm to {updated} event fixtures")
    return 0


if __name__ == "__main__":
    exit(main())
