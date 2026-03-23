#!/usr/bin/env python3
"""
Fetch ASOS from Iowa State Mesonet for ALL East TN events (3,667).
Group by station+year+month to minimize API calls.
Flag ESTIMATED when using nearest station (primary unavailable).
"""

from __future__ import annotations

import csv
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS_PATH = ROOT / "tests" / "fixtures" / "east_tn_full_events.json"
ASOS_DIR = ROOT / "tests" / "fixtures" / "historical_asos"
OBS_DIR = ROOT / "tests" / "fixtures" / "historical_observations"
BASE_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"

KNOTS_TO_MPH = 1.15078
FALLBACK_STATIONS = ["KTYS", "KTRI", "KGKT"]  # Try in order if primary fails


def _asos_row_to_obs(row: dict, station: str) -> dict:
    """Convert ASOS CSV row to GAIA observation format."""
    valid = row.get("valid", "")
    if not valid:
        return {}
    ts = valid.replace(" ", "T") + ":00"
    try:
        from datetime import datetime, timedelta
        dt = datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
        mo = dt.month
        utc_offset = 4 if 3 <= mo <= 10 else 5
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
    obs = {"timestamp": ts, "station_id": station_id, "metar": metar, "sky_condition": skyc1 if skyc1 != "M" else None}
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
    """Fetch one month of ASOS for a station."""
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
        with urllib.request.urlopen(req, timeout=90) as r:
            text = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return []
    lines = [ln for ln in text.strip().split("\n") if ln and not ln.startswith("#")]
    if not lines:
        return []
    reader = csv.DictReader(lines)
    return [_asos_row_to_obs(row, st_short) for row in reader if _asos_row_to_obs(row, st_short).get("timestamp")]


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=50, help="Batch reporting interval")
    ap.add_argument("--delay", type=float, default=0.8, help="Seconds between API calls")
    ap.add_argument("--output", type=str, default=None, help="Output dir for fixtures")
    args = ap.parse_args()
    global OBS_DIR
    if args.output:
        OBS_DIR = Path(args.output)

    if not EVENTS_PATH.exists():
        print("Run export_east_tn_full_events.py first")
        return 1
    events = json.loads(EVENTS_PATH.read_text())
    ASOS_DIR.mkdir(parents=True, exist_ok=True)
    OBS_DIR.mkdir(parents=True, exist_ok=True)

    keys = set()
    for e in events:
        y, m = int(e["date"][:4]), int(e["date"][5:7])
        keys.add((e["station"], y, m))
    keys = sorted(keys)
    print(f"Fetching ASOS for {len(keys)} station-month batches ({len(events)} events)...")

    asos_cache = {}
    for i, (station, year, month) in enumerate(keys):
        fn = ASOS_DIR / f"{station}_{year}_{month:02d}.json"
        if fn.exists():
            asos_cache[(station, year, month)] = json.loads(fn.read_text())
        else:
            st_short = station[1:] if station.startswith("K") else station
            obs_list = fetch_asos_month(st_short, year, month)
            asos_cache[(station, year, month)] = obs_list
            if obs_list:
                fn.write_text(json.dumps(obs_list, indent=2) + "\n")
            if (i + 1) % args.batch_size == 0:
                print(f"  {i+1}/{len(keys)} batches...")
            time.sleep(args.delay)

    built = 0
    estimated = 0
    for event in events:
        eid = event["event_id"]
        date_str = event["date"]
        station = event["station"]
        y, m = int(date_str[:4]), int(date_str[5:7])
        obs_list = asos_cache.get((station, y, m), [])
        day_obs = [o for o in obs_list if o.get("timestamp", "")[:10] == date_str]
        estimated_flag = False
        if not day_obs:
            for fallback in FALLBACK_STATIONS:
                if fallback == station:
                    continue
                obs_fb = asos_cache.get((fallback, y, m), [])
                if not obs_fb and not (ASOS_DIR / f"{fallback}_{y}_{m:02d}.json").exists():
                    obs_fb = fetch_asos_month(fallback[1:], y, m)
                    asos_cache[(fallback, y, m)] = obs_fb
                    if obs_fb:
                        (ASOS_DIR / f"{fallback}_{y}_{m:02d}.json").write_text(json.dumps(obs_fb, indent=2) + "\n")
                day_obs = [o for o in obs_fb if o.get("timestamp", "")[:10] == date_str]
                if day_obs:
                    estimated_flag = True
                    break
        if not day_obs:
            obs_list = asos_cache.get((station, y, m), [])
            day_obs = obs_list
        if not day_obs:
            continue
        day_obs.sort(key=lambda x: x["timestamp"])
        fixture = {
            "event_id": eid,
            "event_date": date_str,
            "event_datetime_utc": event["event_datetime_utc"],
            "station": station,
            "county": event["county"],
            "event_type": event["event_type"],
            "magnitude": event.get("magnitude", ""),
            "observation_count": len(day_obs),
            "observations": day_obs,
            "estimated": estimated_flag,
        }
        out = OBS_DIR / f"event_{eid}.json"
        out.write_text(json.dumps(fixture, indent=2) + "\n")
        built += 1
        if estimated_flag:
            estimated += 1
    print(f"Built {built} observation fixtures ({estimated} ESTIMATED)")
    return 0


if __name__ == "__main__":
    exit(main())
