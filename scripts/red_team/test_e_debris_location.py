#!/usr/bin/env python3
"""
RED TEAM E: Debris / CC feature location vs Mayfield center (survey overlay still required).
"""
from __future__ import annotations

import math
import sys


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


def main() -> int:
    print("=== RED TEAM E: DEBRIS BALL / CC vs MAYFIELD LOCATION ===")
    print()
    mayfield_lat, mayfield_lon = 36.7406, -88.6367
    print(f"Mayfield KY reference (city center): {mayfield_lat}°N {mayfield_lon}°W")
    print()

    # Placeholders: replace with lat/lon from the actual GAIA debris detection log / radar gate.
    debris_lat, debris_lon = 36.75, -88.62
    print(f"Example claimed debris gate (REPLACE with report coordinates): {debris_lat}°N {debris_lon}°W")
    d_km = _haversine_km(debris_lat, debris_lon, mayfield_lat, mayfield_lon)
    print(f"Great-circle distance to Mayfield center: {d_km:.2f} km")
    print()

    if d_km < 5:
        res = "PASS"
        msg = "consistent with Mayfield impact area (still verify vs NWS damage path, not city centroid alone)"
    elif d_km < 15:
        res = "WARN"
        msg = "same mesoscale region — confirm not an earlier/long-track segment without survey overlay"
    else:
        res = "FAIL"
        msg = "too far for an unqualified Mayfield claim"

    print(f"RESULT: {res} — {msg}")
    print()
    print("Required for publication:")
    print("  • NWS damage survey path vertices vs radar gate / correlation centroid")
    print("  • Continuous ground track 08:03 UTC ± volume times")
    print("  • Rule out concurrent debris from a separate storm ID")
    print("  • PAH event summary: https://www.weather.gov/pah/December10-11_2021_TornadoOutbreak")
    return 0 if res != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
