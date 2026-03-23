#!/usr/bin/env python3
"""
Build wildfire fixtures for CA wildfire events.
Uses ASOS observations to derive red flag conditions (RH, wind, temp)
and optional FIRMS data. Merges wildfire_fixture into observation fixtures.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OBS_DIR = ROOT / "tests" / "fixtures" / "national_fire_observations"
EVENTS_PATH = OBS_DIR / "events.json"
FIRMS_PATH = ROOT / "tests" / "fixtures" / "firms_fire" / "firms_usa_latest.csv"

CA_CENTROID = (36.5, -119.5)


def _rh_from_temp_dewpoint(temp_f: float, dewpoint_f: float) -> float:
    """Compute relative humidity % from temp and dewpoint (F)."""
    t_c = (temp_f - 32) * 5 / 9
    d_c = (dewpoint_f - 32) * 5 / 9
    return 100 * math.exp((17.27 * d_c) / (237.3 + d_c) - (17.27 * t_c) / (237.3 + t_c))


def _red_flag_from_obs(obs: dict, soil: float) -> int:
    """Count red flag conditions: RH<15%, wind>15, soil<0.2, temp>90."""
    n = 0
    temp = obs.get("temperature_f")
    dew = obs.get("dewpoint_f")
    if temp is not None and dew is not None:
        rh = _rh_from_temp_dewpoint(temp, dew)
        if rh < 15:
            n += 1
    wind = obs.get("wind_speed_mph") or 0
    if wind > 15:
        n += 1
    if soil < 0.20:
        n += 1
    if temp is not None and temp > 90:
        n += 1
    return n


def main():
    if not EVENTS_PATH.exists():
        print(f"Run fetch_asos_national_backtest for ca_wildfires first. Need {EVENTS_PATH}")
        return 1
    events = json.loads(EVENTS_PATH.read_text())
    built = 0
    for ev in events:
        eid = ev.get("event_id", "")
        if not eid:
            continue
        fixture_path = OBS_DIR / f"event_{eid}.json"
        if not fixture_path.exists():
            continue
        data = json.loads(fixture_path.read_text())
        obs_list = data.get("observations", [])
        soil = 0.15  # Dry - typical CA fire season
        max_rf = 0
        best_obs = None
        for o in obs_list:
            rf = _red_flag_from_obs(o, soil)
            if rf > max_rf:
                max_rf = rf
                best_obs = o
        county_lat = CA_CENTROID[0]
        county_lon = CA_CENTROID[1]
        firms_fires = []
        def _hav(lat1, lon1, lat2, lon2):
            R = 3959
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
            return R * 2 * math.asin(math.sqrt(min(1, a)))
        if FIRMS_PATH.exists():
            import csv
            with open(FIRMS_PATH) as f:
                for row in csv.DictReader(f):
                    try:
                        flat = float(row.get("latitude", 0))
                        flon = float(row.get("longitude", 0))
                        if 32 < flat < 42 and -125 < flon < -114:
                            if _hav(flat, flon, county_lat, county_lon) < 50:
                                frp = float(row.get("frp", 10) or 10)
                                firms_fires.append({"lat": flat, "lon": flon, "frp": frp})
                    except (ValueError, TypeError):
                        pass
        if not firms_fires:
            firms_fires = [{"lat": county_lat, "lon": county_lon, "frp": 300}]
        wf_fixture = {
            "soil_moisture": soil,
            "county_lat": county_lat,
            "county_lon": county_lon,
            "red_flag_conditions_max": max_rf,
            "relative_humidity_pct": _rh_from_temp_dewpoint(best_obs["temperature_f"], best_obs["dewpoint_f"]) if best_obs and best_obs.get("temperature_f") is not None and best_obs.get("dewpoint_f") is not None else None,
            "wind_speed_mph": best_obs.get("wind_speed_mph") if best_obs else None,
            "temperature_f": best_obs.get("temperature_f") if best_obs else None,
            "firms_fires": firms_fires[:20],
        }
        data["wildfire_fixture"] = wf_fixture
        fixture_path.write_text(json.dumps(data, indent=2) + "\n")
        built += 1
    print(f"Built {built} wildfire fixtures")
    return 0


if __name__ == "__main__":
    exit(main())
