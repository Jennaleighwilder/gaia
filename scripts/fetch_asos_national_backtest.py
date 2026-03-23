#!/usr/bin/env python3
"""
Fetch ASOS from Iowa Mesonet for national validation events.
Maps events to nearest ASOS station by lat/lon. Builds observation fixtures
for run_full_backtest (--event-file, --obs-dir).
"""

from __future__ import annotations

import csv
import json
import math
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIONS_PATH = ROOT / "data" / "asos_stations.json"
BASE_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
KNOTS_TO_MPH = 1.15078


def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(min(1, a)))


def _asos_row_to_obs(row: dict, station: str) -> dict:
    valid = row.get("valid", "")
    if not valid:
        return {}
    ts = valid.replace(" ", "T") + ":00"
    try:
        from datetime import datetime, timedelta
        dt = datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
        mo = dt.month
        utc_offset = 5 if 11 <= mo <= 2 else 6  # OK Central
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
    st = f"K{station}" if len(station) == 3 else station
    st_short = st[1:] if st.startswith("K") else st
    url = (
        f"{BASE_URL}?station={st_short}&data=all"
        f"&year1={year}&month1={month}&day1=1"
        f"&year2={year}&month2={month}&day2=28"
        f"&tz=America%2FChicago&format=comma&latlon=yes&elev=yes"
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
    ap.add_argument("--event-file", required=True, help="JSON event file (ok_ef2plus_tornadoes.json etc)")
    ap.add_argument("--output", required=True, help="Output dir for fixtures")
    ap.add_argument("--batch-size", type=int, default=20)
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()

    event_path = Path(args.event_file)
    if not event_path.exists():
        print(f"Event file not found: {event_path}")
        return 1
    events = json.loads(event_path.read_text())
    if not events:
        print("No events in file")
        return 1

    stations_path = args.event_file and Path(args.event_file).parent.parent.parent.parent / "data" / "asos_stations.json"
    stations_path = ROOT / "data" / "asos_stations.json"
    if not stations_path.exists():
        print("Run build_national_station_map.py first to create data/asos_stations.json")
        return 1
    stations = json.loads(stations_path.read_text())
    stations = [s for s in stations if s.get("lat") and s.get("lon")]

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    asos_cache_dir = out_dir / "asos_cache"
    asos_cache_dir.mkdir(exist_ok=True)

    # Enrich events with event_id, station
    enriched = []
    asos_cache = {}
    built = 0
    for i, ev in enumerate(events):
        event_id = f"national_{i}"
        lat = 0.0
        lon = 0.0
        try:
            lat = float(ev.get("lat") or 0)
            lon = float(ev.get("lon") or 0)
        except (ValueError, TypeError):
            pass
        state_abbr = (ev.get("state") or "OK")[:2] if ev.get("state") else "OK"
        if not lat and not lon:
            centroids = {"OK": (35.5, -97.5), "KY": (37.5, -85), "LA": (31, -92), "MO": (37.5, -91.5), "CA": (36.5, -119)}
            lat, lon = centroids.get(state_abbr, centroids["OK"])
        nearest = min(stations, key=lambda s: haversine_mi(lat, lon, float(s["lat"]), float(s["lon"])))
        station_id = nearest["id"]
        st_short = station_id[1:] if station_id.startswith("K") else station_id
        raw_date = (ev.get("date") or "").strip()
        date_str = raw_date[:10]
        if len(date_str) != 10 or date_str[4] != "-":
            try:
                from datetime import datetime
                dt = datetime.strptime(raw_date[:10].strip(), "%d-%b-%y")
                date_str = dt.strftime("%Y-%m-%d")
            except Exception:
                continue
        y, m = int(date_str[:4]), int(date_str[5:7])
        cache_key = (st_short, y, m)
        if cache_key not in asos_cache:
            cache_file = asos_cache_dir / f"{st_short}_{y}_{m:02d}.json"
            if cache_file.exists():
                asos_cache[cache_key] = json.loads(cache_file.read_text())
            else:
                obs_list = fetch_asos_month(st_short, y, m)
                asos_cache[cache_key] = obs_list
                if obs_list:
                    cache_file.write_text(json.dumps(obs_list, indent=2))
                time.sleep(args.delay)
        obs_list = asos_cache.get(cache_key, [])
        day_obs = [o for o in obs_list if o.get("timestamp", "")[:10] == date_str]
        if not day_obs:
            continue
        day_obs.sort(key=lambda x: x["timestamp"])
        station_full = f"K{st_short}" if len(st_short) == 3 else st_short
        fixture = {
            "event_id": event_id,
            "event_date": date_str,
            "event_datetime_utc": f"{date_str}T18:00:00Z",
            "station": station_full,
            "county": (ev.get("county") or "").lower(),
            "event_type": ev.get("event_type", ""),
            "magnitude": ev.get("magnitude", ""),
            "observation_count": len(day_obs),
            "observations": day_obs,
            "estimated": False,
        }
        (out_dir / f"event_{event_id}.json").write_text(json.dumps(fixture, indent=2))
        enriched.append({
            "event_id": event_id,
            "event_datetime_utc": f"{date_str}T18:00:00Z",
            "date": date_str,
            "station": station_full,
            "county": (ev.get("county") or "").lower(),
            "event_type": ev.get("event_type", ""),
            "magnitude": ev.get("magnitude", ""),
        })
        built += 1
        if built % args.batch_size == 0:
            print(f"  Built {built}/{len(events)} fixtures...")

    (out_dir / "events.json").write_text(json.dumps(enriched, indent=2))
    print(f"Built {built} observation fixtures -> {out_dir}")
    return 0


if __name__ == "__main__":
    exit(main())
