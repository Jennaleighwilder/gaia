#!/usr/bin/env python3
"""
Build national terrain profiles for mudslide/landslide engine.
Assigns mean_slope_deg based on physiographic region.
CA Sierra=28, Coast Range=22; WA Cascades=30; CO Rockies=25; OR Coast=24.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "terrain" / "national_terrain.json"

# Physiographic region -> mean_slope_deg, ridge_orientation, valley_flood_risk
REGION_PROFILES = {
    # CA
    "sierra": {"mean_slope_deg": 28, "ridge_orientation_deg": 15, "valley_flood_risk": 0.7},
    "coast range": {"mean_slope_deg": 22, "ridge_orientation_deg": 330, "valley_flood_risk": 0.5},
    "coastal": {"mean_slope_deg": 22, "ridge_orientation_deg": 330, "valley_flood_risk": 0.5},
    "san bernardino": {"mean_slope_deg": 28, "ridge_orientation_deg": 45, "valley_flood_risk": 0.6},
    "san diego": {"mean_slope_deg": 20, "ridge_orientation_deg": 45, "valley_flood_risk": 0.5},
    "santa cruz": {"mean_slope_deg": 24, "ridge_orientation_deg": 330, "valley_flood_risk": 0.6},
    "foothills": {"mean_slope_deg": 18, "ridge_orientation_deg": 15, "valley_flood_risk": 0.6},
    "monterey": {"mean_slope_deg": 22, "ridge_orientation_deg": 330, "valley_flood_risk": 0.5},
    "mendocino": {"mean_slope_deg": 24, "ridge_orientation_deg": 330, "valley_flood_risk": 0.5},
    "kern": {"mean_slope_deg": 22, "ridge_orientation_deg": 45, "valley_flood_risk": 0.5},
    "riverside": {"mean_slope_deg": 24, "ridge_orientation_deg": 45, "valley_flood_risk": 0.5},
    "valley": {"mean_slope_deg": 5, "ridge_orientation_deg": 0, "valley_flood_risk": 0.9},
    # WA
    "cascade": {"mean_slope_deg": 30, "ridge_orientation_deg": 0, "valley_flood_risk": 0.7},
    "olympics": {"mean_slope_deg": 26, "ridge_orientation_deg": 45, "valley_flood_risk": 0.6},
    "seattle": {"mean_slope_deg": 12, "ridge_orientation_deg": 45, "valley_flood_risk": 0.6},
    # CO
    "san juan": {"mean_slope_deg": 28, "ridge_orientation_deg": 45, "valley_flood_risk": 0.6},
    "sawatch": {"mean_slope_deg": 28, "ridge_orientation_deg": 0, "valley_flood_risk": 0.6},
    "gore": {"mean_slope_deg": 26, "ridge_orientation_deg": 45, "valley_flood_risk": 0.6},
    "elk": {"mean_slope_deg": 25, "ridge_orientation_deg": 45, "valley_flood_risk": 0.5},
    "flattop": {"mean_slope_deg": 24, "ridge_orientation_deg": 45, "valley_flood_risk": 0.5},
    "chaffee": {"mean_slope_deg": 26, "ridge_orientation_deg": 0, "valley_flood_risk": 0.6},
    "boulder": {"mean_slope_deg": 22, "ridge_orientation_deg": 45, "valley_flood_risk": 0.7},
    "grand": {"mean_slope_deg": 24, "ridge_orientation_deg": 45, "valley_flood_risk": 0.5},
    "summit": {"mean_slope_deg": 26, "ridge_orientation_deg": 0, "valley_flood_risk": 0.6},
    # OR
    "oregon coast": {"mean_slope_deg": 24, "ridge_orientation_deg": 330, "valley_flood_risk": 0.5},
    "columbia gorge": {"mean_slope_deg": 28, "ridge_orientation_deg": 90, "valley_flood_risk": 0.7},
    "central oregon": {"mean_slope_deg": 18, "ridge_orientation_deg": 0, "valley_flood_risk": 0.4},
    "portland": {"mean_slope_deg": 12, "ridge_orientation_deg": 45, "valley_flood_risk": 0.5},
    # KY/TN
    "estill": {"mean_slope_deg": 14, "ridge_orientation_deg": 45, "valley_flood_risk": 0.7},
    "powell": {"mean_slope_deg": 16, "ridge_orientation_deg": 45, "valley_flood_risk": 0.7},
    "pike": {"mean_slope_deg": 18, "ridge_orientation_deg": 45, "valley_flood_risk": 0.8},
}


def _best_match(region: str) -> dict:
    """Return best matching profile for zone string."""
    r = (region or "").lower().strip()
    # Try exact key match first
    for key, profile in REGION_PROFILES.items():
        if key in r or r in key:
            return profile.copy()
    # Keyword fallback
    if "sierra" in r or "mtns" in r or "mtn" in r:
        return REGION_PROFILES["sierra"].copy()
    if "cascade" in r:
        return REGION_PROFILES["cascade"].copy()
    if "coast" in r or "coastal" in r:
        return REGION_PROFILES["coast range"].copy()
    if "san juan" in r:
        return REGION_PROFILES["san juan"].copy()
    if "olympics" in r:
        return REGION_PROFILES["olympics"].copy()
    if "foothills" in r:
        return REGION_PROFILES["foothills"].copy()
    if "valley" in r and "river" not in r:
        return REGION_PROFILES["valley"].copy()
    return {"mean_slope_deg": 12, "ridge_orientation_deg": 45, "valley_flood_risk": 0.5}


def main():
    from collections import defaultdict
    # Build key -> profile for all unique zone strings from landslide corpus
    landslide_path = ROOT / "tests" / "fixtures" / "usgs_landslides" / "landslide_events.json"
    zones = set()
    if landslide_path.exists():
        events = json.loads(landslide_path.read_text())
        for e in events:
            c = (e.get("county") or "").strip()
            if c:
                zones.add(c.lower())
    # Add common keys for keyword lookup
    result = {}
    for z in sorted(zones):
        key = z.replace(" ", "_").replace("/", "_").replace("-", "_")[:60]
        result[key] = _best_match(z)
    # Also add short keyword keys for flexible matching
    for kw, profile in REGION_PROFILES.items():
        key = kw.replace(" ", "_")
        if key not in result:
            result[key] = profile.copy()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2))
    print(f"Built {len(result)} terrain profiles -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    exit(main())
