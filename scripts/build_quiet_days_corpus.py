#!/usr/bin/env python3
"""
Build 200+ quiet days: 5 per month from 1996-2025 with no storm events in East TN.
Fetch ASOS for those days. Output: tests/fixtures/historical_observations/quiet_*.json
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))
EVENTS_PATH = ROOT / "tests" / "fixtures" / "east_tn_full_events.json"
ASOS_DIR = ROOT / "tests" / "fixtures" / "historical_asos"
OBS_DIR = ROOT / "tests" / "fixtures" / "historical_observations"
STATIONS = ["KTYS", "KTRI", "KGKT"]


def load_event_dates() -> set[str]:
    """Return set of dates (YYYY-MM-DD) that have storm events."""
    if not EVENTS_PATH.exists():
        return set()
    events = json.loads(EVENTS_PATH.read_text())
    return {e["date"] for e in events}


def sample_quiet_days(n_per_month: int = 5) -> list[tuple[str, str]]:
    """Sample n_per_month quiet days per (year, month). Returns [(date, station), ...]."""
    event_dates = load_event_dates()
    result = []
    for year in range(1996, 2026):
        for month in range(1, 13):
            try:
                days_in_month = (datetime(year, month % 12 + 1, 1) - timedelta(days=1)).day
            except (ValueError, TypeError):
                days_in_month = 28 if month == 2 else 30 if month in (4, 6, 9, 11) else 31
            candidates = []
            for day in range(1, days_in_month + 1):
                try:
                    dt = datetime(year, month, day)
                    date_str = dt.strftime("%Y-%m-%d")
                    if date_str not in event_dates:
                        candidates.append(date_str)
                except ValueError:
                    continue
            if not candidates:
                continue
            sampled = random.sample(candidates, min(n_per_month, len(candidates)))
            for date_str in sampled:
                station = STATIONS[hash(date_str) % len(STATIONS)]
                result.append((date_str, station))
    return result


def main():
    quiet_days = sample_quiet_days(5)
    print(f"Sampled {len(quiet_days)} quiet days")
    OBS_DIR.mkdir(parents=True, exist_ok=True)
    # We need to fetch ASOS for each unique (station, year, month)
    # For now, write placeholder fixtures - real fetch done by fetch_asos_full_backtest
    # or a dedicated quiet-day ASOS fetcher
    from scripts.fetch_asos_full_backtest import fetch_asos_month
    import time
    import csv
    built = 0
    keys = set()
    for date_str, station in quiet_days:
        y, m = int(date_str[:4]), int(date_str[5:7])
        keys.add((station, y, m))
    print(f"Unique station-months to fetch: {len(keys)}")
    asos_cache = {}
    for i, (station, year, month) in enumerate(sorted(keys)):
        fn = ASOS_DIR / f"{station}_{year}_{month:02d}.json"
        if fn.exists():
            asos_cache[(station, year, month)] = json.loads(fn.read_text())
        else:
            st_short = station[1:] if station.startswith("K") else station
            obs_list = fetch_asos_month(st_short, year, month)
            asos_cache[(station, year, month)] = obs_list
            if obs_list:
                fn.write_text(json.dumps(obs_list, indent=2) + "\n")
            if (i + 1) % 20 == 0:
                print(f"  Fetched {i+1}/{len(keys)}...")
            time.sleep(0.8)
    for date_str, station in quiet_days:
        y, m = int(date_str[:4]), int(date_str[5:7])
        obs_list = asos_cache.get((station, y, m), [])
        day_obs = [o for o in obs_list if o.get("timestamp", "")[:10] == date_str]
        if not day_obs:
            day_obs = obs_list
        if not day_obs:
            continue
        day_obs.sort(key=lambda x: x["timestamp"])
        slug = date_str.replace("-", "")
        fixture = {
            "quiet_id": f"quiet_{slug}_{station}",
            "date": date_str,
            "station": station,
            "observation_count": len(day_obs),
            "observations": day_obs,
        }
        out = OBS_DIR / f"quiet_{slug}_{station}.json"
        out.write_text(json.dumps(fixture, indent=2) + "\n")
        built += 1
    print(f"Built {built} quiet day fixtures")


if __name__ == "__main__":
    random.seed(42)
    main()
