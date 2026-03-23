"""
EPA Toxics Release Inventory (TRI) facility data for East TN.
Loaded from fixture populated by scripts/populate_tri_fixture.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "tri_facilities_tn.json"


def load_fixture() -> dict:
    """Load TRI fixture: { facilities: [...], count: int }."""
    if not FIXTURE_PATH.exists():
        return {"facilities": [], "count": 0}
    try:
        return json.loads(FIXTURE_PATH.read_text())
    except Exception:
        return {"facilities": [], "count": 0}


def _haversine_miles(lat: float, lon: float, fl: float, fo: float) -> float:
    import math
    R = 3959
    dlat = math.radians(lat - fl)
    dlon = math.radians(lon - fo)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(fl)) * math.cos(math.radians(lat)) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(min(1, a)))
    return R * c


def get_facilities_in_radius(lat: float, lon: float, radius_miles: float = 10.0) -> list[dict]:
    """
    Return TRI facilities within radius of (lat, lon).
    Uses Haversine. Includes distance_miles and has_class1.
    """
    data = load_fixture()
    facilities = data.get("facilities", [])
    out = []
    for f in facilities:
        fl, fo = f.get("lat"), f.get("lon")
        if fl is None or fo is None:
            continue
        dist = _haversine_miles(lat, lon, fl, fo)
        if dist <= radius_miles:
            out.append({**f, "distance_miles": round(dist, 2)})
    return sorted(out, key=lambda x: x.get("distance_miles", 999))


def has_class1_within_radius(lat: float, lon: float, radius_miles: float = 5.0) -> bool:
    """True if any facility with Class 1 chemicals (flammable, explosive, toxic gas) is within radius."""
    facilities = get_facilities_in_radius(lat, lon, radius_miles)
    return any(f.get("has_class1") for f in facilities)
