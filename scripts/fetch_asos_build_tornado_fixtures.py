#!/usr/bin/env python3
"""
Fetch ASOS from Iowa State Mesonet (batched by station+month).
Build tornado event fixtures in historical_observations/.
"""

from __future__ import annotations

import csv
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TORNADO_EVENTS = ROOT / "tests" / "fixtures" / "east_tn_tornado_events.json"
ASOS_DIR = ROOT / "tests" / "fixtures" / "historical_asos"
OBS_DIR = ROOT / "tests" / "fixtures" / "historical_observations"
BASE_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"

KNOTS_TO_MPH = 1.15078


def _asos_row_to_obs(row: dict, station: str) -> dict:
    """Convert ASOS CSV row to GAIA observation format."""
    valid = row.get("valid", "")
    if not valid:
        return {}
    # valid format: "2023-08-07 00:53" in America/New_York (Eastern)
    # EDT = UTC-4, EST = UTC-5. Approximate: add 4 for Mar-Oct, 5 for Nov-Feb
    ts = valid.replace(" ", "T") + ":00"
    try:
        from datetime import datetime, timedelta
        dt = datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
        mo = dt.month
        utc_offset = 4 if 3 <= mo <= 10 else 5  # EDT vs EST
        dt_utc = dt + timedelta(hours=utc_offset)
        ts = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass
    tmpf = row.get("tmpf", "M")
    dwpf = row.get("dwpf", "M")
    mslp = row.get("mslp", "M")
    drct = row.get("drct", "M")
    sknt = row.get("sknt", "M")
    gust = row.get("gust", "M")
    vsby = row.get("vsby", "M")
    p01i = row.get("p01i", "M")
    skyc1 = row.get("skyc1", "") or "M"
    metar = row.get("metar", "")
    station_id = f"K{station}" if len(station) == 3 else station
    obs = {
        "timestamp": ts,
        "station_id": station_id,
        "metar": metar,
        "sky_condition": skyc1 if skyc1 != "M" else None,
    }
    try:
        if tmpf != "M":
            obs["temperature_f"] = float(tmpf)
    except (ValueError, TypeError):
        pass
    try:
        if dwpf != "M":
            obs["dewpoint_f"] = float(dwpf)
    except (ValueError, TypeError):
        pass
    try:
        if mslp != "M":
            obs["pressure_mb"] = float(mslp)
    except (ValueError, TypeError):
        pass
    try:
        if drct != "M":
            obs["wind_direction_deg"] = float(drct)
    except (ValueError, TypeError):
        pass
    try:
        if sknt != "M":
            obs["wind_speed_mph"] = float(sknt) * KNOTS_TO_MPH
    except (ValueError, TypeError):
        pass
    try:
        if gust != "M":
            obs["wind_gust_mph"] = float(gust) * KNOTS_TO_MPH
    except (ValueError, TypeError):
        obs["wind_gust_mph"] = None
    try:
        if vsby != "M":
            obs["visibility_mi"] = float(vsby)
    except (ValueError, TypeError):
        pass
    try:
        if p01i == "T":
            obs["precip_1h_in"] = 0.0001
        elif p01i != "M":
            obs["precip_1h_in"] = float(p01i)
    except (ValueError, TypeError):
        obs["precip_1h_in"] = 0.0
    return obs


def fetch_asos_month(station: str, year: int, month: int) -> list[dict]:
    """Fetch one month of ASOS for a station. Returns list of obs dicts."""
    st = f"K{station}" if len(station) == 3 else station
    st_short = st[1:] if st.startswith("K") else st
    url = (
        f"{BASE_URL}?station={st_short}&data=all"
        f"&year1={year}&month1={month}&day1=1"
        f"&year2={year}&month2={month}&day2=28"
        f"&tz=America%2FNew_York&format=comma&latlon=yes&elev=yes"
        f"&missing=M&trace=T&direct=no&report_type=3"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  Fetch failed {st} {year}-{month}: {e}")
        return []
    lines = [ln for ln in text.strip().split("\n") if ln and not ln.startswith("#")]
    if not lines:
        return []
    reader = csv.DictReader(lines)
    obs_list = []
    for row in reader:
        obs = _asos_row_to_obs(row, st_short)
        if obs.get("timestamp"):
            obs_list.append(obs)
    return obs_list


def main():
    if not TORNADO_EVENTS.exists():
        print("Run export_east_tn_tornado_events.py first")
        return
    events = json.loads(TORNADO_EVENTS.read_text())
    ASOS_DIR.mkdir(parents=True, exist_ok=True)
    OBS_DIR.mkdir(parents=True, exist_ok=True)

    # Collect unique station+year+month
    keys = set()
    for e in events:
        y, m = int(e["date"][:4]), int(e["date"][5:7])
        keys.add((e["station"], y, m))

    # Fetch ASOS by month
    asos_cache = {}
    for (station, year, month) in sorted(keys):
        fn = ASOS_DIR / f"{station}_{year}_{month:02d}.json"
        if fn.exists():
            asos_cache[(station, year, month)] = json.loads(fn.read_text())
            continue
        print(f"Fetching {station} {year}-{month}...")
        st_short = station[1:] if station.startswith("K") else station
        obs_list = fetch_asos_month(station, year, month)
        asos_cache[(station, year, month)] = obs_list
        if obs_list:
            fn.write_text(json.dumps(obs_list, indent=2) + "\n")
        time.sleep(1)

    # Build event fixtures
    built = 0
    for event in events:
        eid = event["event_id"]
        date_str = event["date"]
        station = event["station"]
        y, m = int(date_str[:4]), int(date_str[5:7])
        obs_list = asos_cache.get((station, y, m), [])
        day_obs = [o for o in obs_list if o.get("timestamp", "")[:10] == date_str]
        if not day_obs:
            day_obs = obs_list
        if not day_obs:
            print(f"  No ASOS for {eid} {date_str} {station}")
            continue
        day_obs.sort(key=lambda x: x["timestamp"])
        fixture = {
            "event_id": eid,
            "event_date": date_str,
            "event_datetime_utc": event["event_datetime_utc"],
            "station": station,
            "county": event["county"],
            "event_type": "tornado",
            "magnitude": event["magnitude"],
            "observation_count": len(day_obs),
            "observations": day_obs,
        }
        out = OBS_DIR / f"event_{eid}.json"
        out.write_text(json.dumps(fixture, indent=2) + "\n")
        built += 1
    print(f"Built {built} tornado fixtures in {OBS_DIR}")


if __name__ == "__main__":
    main()
