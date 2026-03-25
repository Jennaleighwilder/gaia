#!/usr/bin/env python3
"""
Fetch ASOS from Iowa State Mesonet for ALL East TN events (3,667).
Group by station+year+month to minimize API calls.
Flag ESTIMATED when using nearest station (primary unavailable).
"""

from __future__ import annotations

import calendar
import csv
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EVENTS_PATH = ROOT / "tests" / "fixtures" / "east_tn_full_events.json"
DEFAULT_ASOS_DIR = ROOT / "tests" / "fixtures" / "historical_asos"
DEFAULT_OBS_DIR = ROOT / "tests" / "fixtures" / "historical_observations"
STATIONS_PATH = ROOT / "data" / "asos_stations.json"
BASE_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"

KNOTS_TO_MPH = 1.15078
FALLBACK_STATIONS = ["KTYS", "KTRI", "KGKT"]  # Try in order if primary fails


def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(min(1, a)))


def nearest_asos_station(lat: float, lon: float, stations: list[dict]) -> str:
    """Return station id e.g. KOKC (with K prefix)."""
    nearest = min(stations, key=lambda s: haversine_mi(lat, lon, float(s["lat"]), float(s["lon"])))
    sid = nearest["id"]
    return f"K{sid}" if len(sid) == 3 and not sid.startswith("K") else sid


def _asos_row_to_obs(row: dict, station: str, *, utc: bool = False) -> dict:
    """Convert ASOS CSV row to GAIA observation format."""
    valid = row.get("valid", "")
    if not valid:
        return {}
    if utc:
        # Mesonet often omits seconds: "1950-04-01 00:00" -> need full ISO for comparisons
        ts = valid.replace(" ", "T").strip()
        if len(ts) >= 19:
            ts = ts[:19] + "Z"
        elif len(ts) == 16:
            ts = ts + ":00Z"
        else:
            return {}
    else:
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


def fetch_asos_month(
    station: str, year: int, month: int, *, tz: str = "America/New_York", utc: bool = False
) -> list[dict]:
    """Fetch one month of ASOS for a station (full month via calendar)."""
    st = f"K{station}" if len(station) == 3 else station
    st_short = st[1:] if st.startswith("K") else station
    _, last_day = calendar.monthrange(year, month)
    tz_q = urllib.parse.quote(tz, safe="")
    url = (
        f"{BASE_URL}?station={st_short}&data=all"
        f"&year1={year}&month1={month}&day1=1"
        f"&year2={year}&month2={month}&day2={last_day}"
        f"&tz={tz_q}&format=comma&latlon=yes&elev=yes"
        f"&missing=M&trace=T&direct=no&report_type=3"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
        with urllib.request.urlopen(req, timeout=90) as r:
            text = r.read().decode("utf-8", errors="replace")
    except Exception:
        return []
    lines = [ln for ln in text.strip().split("\n") if ln and not ln.startswith("#")]
    if not lines:
        return []
    reader = csv.DictReader(lines)
    return [
        _asos_row_to_obs(row, st_short, utc=utc)
        for row in reader
        if _asos_row_to_obs(row, st_short, utc=utc).get("timestamp")
    ]


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--event-file", type=str, default=None, help="Event JSON (default: east_tn_full_events.json)")
    ap.add_argument(
        "--obs-dir",
        "--output",
        type=str,
        default=None,
        dest="obs_dir",
        help="Directory for event_{event_id}.json fixtures (default: historical_observations)",
    )
    ap.add_argument("--asos-cache-dir", type=str, default=None, help="Month ASOS cache JSON dir")
    ap.add_argument("--batch-size", type=int, default=50, help="Batch reporting interval")
    ap.add_argument("--delay", type=float, default=0.8, help="Seconds between API calls")
    ap.add_argument(
        "--max-events",
        type=int,
        default=None,
        metavar="N",
        help="Process only the first N events after normalization (smoke test)",
    )
    ap.add_argument(
        "--skip-existing",
        action="store_true",
        default=False,
        help="Skip events whose fixture file already exists in obs-dir",
    )
    args = ap.parse_args()

    events_path = Path(args.event_file) if args.event_file else DEFAULT_EVENTS_PATH
    obs_dir = Path(args.obs_dir) if args.obs_dir else DEFAULT_OBS_DIR
    asos_dir = Path(args.asos_cache_dir) if args.asos_cache_dir else DEFAULT_ASOS_DIR

    if not events_path.exists():
        print(f"Event file not found: {events_path}")
        return 1
    events = json.loads(events_path.read_text())
    asos_dir.mkdir(parents=True, exist_ok=True)
    obs_dir.mkdir(parents=True, exist_ok=True)

    national_mode = args.event_file is not None and events_path.resolve() != DEFAULT_EVENTS_PATH.resolve()
    stations_list: list[dict] = []
    if STATIONS_PATH.exists():
        stations_list = [s for s in json.loads(STATIONS_PATH.read_text()) if s.get("lat") and s.get("lon")]
    if any(
        (not e.get("station")) and float(e.get("lat") or 0) and float(e.get("lon") or 0)
        for e in events
    ):
        if not stations_list:
            print("Need data/asos_stations.json for nearest-station lookup")
            return 1

    # Normalize events: event_id, date, station, event_datetime_utc
    norm: list[dict] = []
    for i, e in enumerate(events):
        eid = e.get("event_id")
        if not eid:
            eid = f"event_{i}"
        date_str = (e.get("date") or "")[:10]
        if len(date_str) != 10 or date_str[4] != "-":
            continue
        station = e.get("station")
        try:
            lat = float(e.get("lat") or 0)
            lon = float(e.get("lon") or 0)
        except (TypeError, ValueError):
            lat, lon = 0.0, 0.0
        if not station and lat and lon and stations_list:
            station = nearest_asos_station(lat, lon, stations_list)
        if not station:
            continue
        if not str(station).startswith("K") and len(str(station)) == 3:
            station = f"K{station}"
        edt = e.get("event_datetime_utc") or f"{date_str}T18:00:00Z"
        norm.append(
            {
                **e,
                "event_id": eid,
                "date": date_str,
                "station": station,
                "event_datetime_utc": edt,
            }
        )

    if args.max_events is not None and args.max_events > 0:
        norm = norm[: args.max_events]

    if args.skip_existing:
        before = len(norm)
        norm = [e for e in norm if not (obs_dir / f"event_{e['event_id']}.json").exists()]
        skipped_pre = before - len(norm)
        print(f"--skip-existing: {skipped_pre} already on disk, {len(norm)} remaining", flush=True)

    use_utc = bool(national_mode)
    tz = "UTC" if use_utc else "America/New_York"

    keys = set()
    for e in norm:
        y, m = int(e["date"][:4]), int(e["date"][5:7])
        st = e["station"]
        keys.add((st, y, m))
    keys = sorted(keys)
    print(
        f"Fetching ASOS for {len(keys)} station-month batches ({len(norm)} events, tz={tz})...",
        flush=True,
    )

    asos_cache: dict = {}
    for i, (station, year, month) in enumerate(keys):
        cache_name = f"{station}_{year}_{month:02d}_{'utc' if use_utc else 'et'}.json"
        fn = asos_dir / cache_name
        st_short = station[1:] if str(station).startswith("K") else station
        if fn.exists():
            asos_cache[(station, year, month)] = json.loads(fn.read_text())
        else:
            obs_list = fetch_asos_month(st_short, year, month, tz=tz, utc=use_utc)
            asos_cache[(station, year, month)] = obs_list
            if obs_list:
                fn.write_text(json.dumps(obs_list, indent=2) + "\n")
            if (i + 1) % args.batch_size == 0:
                print(f"  {i + 1}/{len(keys)} batches...")
            time.sleep(args.delay)

    built = 0
    estimated = 0
    for event in norm:
        eid = event["event_id"]
        date_str = event["date"]
        station = event["station"]
        y, m = int(date_str[:4]), int(date_str[5:7])
        obs_list = asos_cache.get((station, y, m), [])
        day_obs = [o for o in obs_list if o.get("timestamp", "")[:10] == date_str]
        estimated_flag = False
        if not day_obs and not national_mode:
            for fallback in FALLBACK_STATIONS:
                if fallback == station:
                    continue
                obs_fb = asos_cache.get((fallback, y, m), [])
                cache_fb = asos_dir / f"{fallback}_{y}_{m:02d}_{'utc' if use_utc else 'et'}.json"
                if not obs_fb and not cache_fb.exists():
                    obs_fb = fetch_asos_month(fallback[1:], y, m, tz=tz, utc=use_utc)
                    asos_cache[(fallback, y, m)] = obs_fb
                    if obs_fb:
                        cache_fb.write_text(json.dumps(obs_fb, indent=2) + "\n")
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
            "county": event.get("county", ""),
            "event_type": event.get("event_type", ""),
            "magnitude": event.get("magnitude", ""),
            "observation_count": len(day_obs),
            "observations": day_obs,
            "estimated": estimated_flag,
        }
        out = obs_dir / f"event_{eid}.json"
        out.write_text(json.dumps(fixture, indent=2) + "\n")
        built += 1
        if estimated_flag:
            estimated += 1
        if built % args.batch_size == 0:
            print(f"  wrote {built} event_*.json fixtures...")
    print(f"Built {built} observation fixtures -> {obs_dir} ({estimated} ESTIMATED)")
    return 0


if __name__ == "__main__":
    exit(main())
