#!/usr/bin/env python3
"""
Build national county-to-ASOS station mapping.
Uses Iowa State Mesonet ASOS1MIN network (917 stations nationwide).
"""

from __future__ import annotations

import json
import math
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "tests" / "fixtures" / "national_station_map.json"

# Try api/1 first (new format); fallback to geojson/network (stid/sid, sname)
API_URL = "https://mesonet.agron.iastate.edu/api/1/stations.geojson?network=ASOS"
FALLBACK_URL = "https://mesonet.agron.iastate.edu/geojson/network.py?network=ASOS1MIN"


def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(min(1, a)))


def main():
    geojson = None
    for url, label in [(API_URL, "api/1 ASOS"), (FALLBACK_URL, "geojson ASOS1MIN")]:
        try:
            print(f"Fetching ASOS station list from Iowa Mesonet ({label})...")
            req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                geojson = json.loads(r.read().decode())
            break
        except Exception as e:
            print(f"  {label} failed: {e}")
    if not geojson:
        raise SystemExit("Could not fetch ASOS stations")
    stations = []
    for f in geojson.get("features", []):
        props = f.get("properties", {})
        coords = f.get("geometry", {}).get("coordinates", [0, 0])
        lon, lat = float(coords[0]), float(coords[1])
        if lat and lon:
            stations.append({
                "id": props.get("stid") or props.get("sid", ""),
                "name": props.get("sname", ""),
                "lon": lon,
                "lat": lat,
                "state": props.get("state", ""),
                "county": props.get("county", ""),
            })
    print(f"Loaded {len(stations)} ASOS stations")

    # Save raw station list for other scripts
    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "asos_stations.json").write_text(json.dumps([{"id": s["id"], "name": s["name"], "lat": s["lat"], "lon": s["lon"], "state": s["state"]} for s in stations], indent=2))
    print("Saved to data/asos_stations.json")

    # County centroids: East TN + national validation states
    COUNTY_CENTROIDS = [
        ("knox", "TN", 35.9606, -83.9207), ("sevier", "TN", 35.8689, -83.5235),
        ("blount", "TN", 35.6878, -83.9254), ("greene", "TN", 36.1960, -82.8110),
        ("hamblen", "TN", 36.1794, -83.3754), ("hawkins", "TN", 36.3712, -82.1734),
        ("washington", "TN", 36.2929, -82.4971), ("grainger", "TN", 36.2666, -83.5081),
        ("sullivan", "TN", 36.4752, -82.4074), ("anderson", "TN", 36.0230, -84.2336),
        ("cook", "IL", 41.8401, -87.8168), ("harris", "TX", 29.7752, -95.3103),
        ("tulsa", "OK", 36.1539, -95.9928), ("oklahoma", "OK", 35.5514, -97.4075),
        ("los angeles", "CA", 34.0522, -118.2437), ("orleans", "LA", 29.9511, -90.0715),
        ("king", "WA", 47.4900, -121.8344), ("denver", "CO", 39.7392, -104.9903),
        ("miami-dade", "FL", 25.7743, -80.1937), ("st. louis", "MO", 38.6270, -90.1994),
        ("jefferson", "KY", 38.2527, -85.7645), ("pulaski", "AR", 34.7465, -92.2896),
    ]

    result = {}
    for county, state_abbr, lat, lon in COUNTY_CENTROIDS:
        valid = [s for s in stations if s.get("lat") and s.get("lon")]
        if not valid:
            continue
        nearest = min(valid, key=lambda s: haversine_mi(lat, lon, s["lat"], s["lon"]))
        key = f"{county}_{state_abbr}".lower().replace(" ", "_").replace(".", "")
        result[key] = {
            "county": county,
            "state": state_abbr,
            "station_id": nearest["id"],
            "station_name": nearest["name"],
            "distance_mi": round(haversine_mi(lat, lon, nearest["lat"], nearest["lon"]), 2),
        }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2))
    print(f"Built map for {len(result)} counties -> {OUT_PATH}")


if __name__ == "__main__":
    main()
