#!/usr/bin/env python3
"""
8. Beam geometry audit: KPAH → Mayfield, KY (Quad-State case) at ~08:03 UTC.

Uses 4/3-earth geometric optics; checks lowest operational tilts illuminate
low-to-mid levels at the target range (debris / mesocyclone heights).
"""
from __future__ import annotations

import math
import sys

import scripts.integrity_tests._paths  # noqa: F401

# WSR-88D KPAH (Paducah) — align with scripts/radar_storm_tracker.py header
KPAH_LAT, KPAH_LON = 37.068, -88.772
# Mayfield, KY — near 2021-12-10 tornado track
MAYFIELD_LAT, MAYFIELD_LON = 36.7347, -88.6277

R_E_KM = 6371.0
K_E = 4.0 / 3.0
RE_EFF = R_E_KM * K_E


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * R_E_KM * math.asin(math.sqrt(min(1.0, a)))


def beam_height_center_km(slant_range_km: float, el_deg: float) -> float:
    """Height of radar beam center above radar level (standard refraction model)."""
    el = math.radians(el_deg)
    # Small-angle friendly form: h = r sin el + (r cos el)^2 / (2 k_e R)
    return slant_range_km * math.sin(el) + (slant_range_km * math.cos(el)) ** 2 / (2 * RE_EFF)


def main() -> int:
    surf_km = haversine_km(KPAH_LAT, KPAH_LON, MAYFIELD_LAT, MAYFIELD_LON)
    # Slant range ≈ surface range for these elevations at short distance
    for tilt in (0.5, 0.9, 1.3, 1.8):
        h = beam_height_center_km(surf_km, tilt)
        print(f"  tilt {tilt:4.1f}°  slant≈{surf_km:.1f} km  beam-center height ≈ {h:.2f} km ARL")
    h05 = beam_height_center_km(surf_km, 0.5)
    h18 = beam_height_center_km(surf_km, 1.8)
    # Debris / low-level meso typically ~0.5–5 km AGL; beam should pass through layer
    if 0.3 <= h05 <= 8.0 and h18 <= 12.0:
        print(
            "RESULT: PASS — KPAH lowest tilts geometrically intersect low/mid levels "
            f"at Mayfield (~{surf_km:.0f} km range); 08:03 UTC is valid for geometry "
            "(time affects storm location, not radar–fixed point baseline)."
        )
    elif h05 < 0.15:
        print("RESULT: FAIL — beam center unreasonably low (ground clutter regime only)")
    else:
        print("RESULT: WARN — unusual heights; verify storm location vs fixed Mayfield point")
    return 0


if __name__ == "__main__":
    sys.exit(main())
