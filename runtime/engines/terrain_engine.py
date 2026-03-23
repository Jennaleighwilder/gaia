"""
SRTM Terrain Engine — Tier 1

East TN ridges run NE-SW. Wind from WSW hitting ridges = orographic lift.
Pre-compute: slope, ridge orientation, valley elevation, roughness.
Runtime: orographic lift, flood risk, wind enhancement.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
DEM_DIR = ROOT / "data" / "terrain"
EAST_TN_RIDGE_ANGLE = 45.0  # NE-SW = ~45 deg from N

# County centroids (approx) for fallback when no DEM
COUNTY_CENTROIDS = {
    "knox": (35.96, -83.99),
    "sevier": (35.78, -83.52),
    "blount": (35.69, -83.93),
    "greene": (36.17, -82.83),
    "hamblen": (36.22, -83.27),
    "hawkins": (36.44, -82.95),
    "washington": (36.30, -82.50),
    "grainger": (36.28, -83.51),
    "sullivan": (36.51, -82.30),
    "anderson": (36.11, -84.20),
}


COUNTY_SLOPES_OVERRIDE = {
    "sevier": 22.0, "blount": 18.0, "hawkins": 16.0,
    "grainger": 15.0, "greene": 12.0,
}


def _load_national_terrain() -> dict:
    """Load national terrain profiles (CA, WA, CO, OR slopes)."""
    path = DEM_DIR / "national_terrain.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _match_national_region(region: str, national: dict) -> dict | None:
    """Match region string to national terrain profile."""
    r = (region or "").lower().strip()
    if not r:
        return None
    r_norm = r.replace(" ", "_").replace("/", "_").replace("-", "_")[:80]
    if r_norm in national:
        return national[r_norm].copy()
    for k, v in national.items():
        if r_norm in k or k in r_norm:
            return v.copy()
    if "sierra" in r:
        return national.get("sierra", {})
    if "cascade" in r:
        return national.get("cascade", {})
    if "san juan" in r or "sawatch" in r:
        return national.get("san_juan", national.get("sawatch", {}))
    if "coast" in r or "coastal" in r:
        return national.get("coast_range", national.get("coastal", {}))
    return None


def _load_terrain_cache() -> dict:
    """Load pre-computed terrain stats per county."""
    cache_path = DEM_DIR / "east_tn_terrain.json"
    result = {}
    if cache_path.exists():
        try:
            result = json.loads(cache_path.read_text())
        except Exception:
            pass
    for c, slope in COUNTY_SLOPES_OVERRIDE.items():
        if c not in result:
            result[c] = {}
        result[c]["mean_slope_deg"] = slope
        result[c]["max_slope_deg"] = result[c].get("max_slope_deg", slope + 15)
    national = _load_national_terrain()
    result["_national"] = national
    if not result:
        result = {
            c: {
                "mean_slope_deg": COUNTY_SLOPES_OVERRIDE.get(c, 8.0),
                "ridge_orientation_deg": 45.0,
                "valley_elev_m": 350.0,
                "terrain_roughness": 0.4,
                "max_slope_deg": COUNTY_SLOPES_OVERRIDE.get(c, 25.0) + 10,
            }
            for c in COUNTY_CENTROIDS
        }
    return result


_TERRAIN_CACHE: dict | None = None


def get_terrain_stats(region: str) -> dict:
    global _TERRAIN_CACHE
    if _TERRAIN_CACHE is None:
        _TERRAIN_CACHE = _load_terrain_cache()
    r = region.lower() if region else ""
    out = _TERRAIN_CACHE.get(r)
    if out:
        return out
    national = _TERRAIN_CACHE.get("_national", {})
    nat = _match_national_region(region, national)
    if nat:
        nat.setdefault("max_slope_deg", nat.get("mean_slope_deg", 15) + 15)
        nat.setdefault("valley_elev_m", 500)
        nat.setdefault("terrain_roughness", 0.5)
        return nat
    return _TERRAIN_CACHE.get("knox", {})


class TerrainEngine:
    """Tier 1: Orographic lift, flood accumulation, wind enhancement."""

    def __init__(self):
        self.history = {}

    def ingest(self, region: str, timestamp: str, **data) -> None:
        self.history.setdefault(region, []).append({"timestamp": timestamp, **data})
        if len(self.history[region]) > 24:
            self.history[region] = self.history[region][-24:]

    def score(self, region: str, payload: dict | None = None, **kwargs) -> dict:
        stats = get_terrain_stats(region)
        slope = stats.get("mean_slope_deg", 8.0)
        ridge_angle = stats.get("ridge_orientation_deg", 45.0)
        wind_dir = payload.get("wind_direction_deg") if payload else None
        wind_speed = payload.get("wind_speed_mph") if payload else 0.0
        rainfall_rate = payload.get("rainfall_rate_in_hr") or 0.0
        # Orographic lift: wind perpendicular to ridge = max
        if wind_dir is not None and wind_speed and wind_speed > 10:
            angle_diff = abs((wind_dir - ridge_angle) % 180 - 90)
            if angle_diff < 30:
                orographic = 0.3 + 0.7 * (slope / 25.0) * (wind_speed / 30.0)
            else:
                orographic = 0.1 * (slope / 25.0)
        else:
            orographic = 0.1 * (slope / 25.0)
        # Valley flood risk: slope + rainfall
        flood_risk = min(1.0, 0.2 + (slope / 30.0) * 0.3 + rainfall_rate * 0.8)
        # Wind enhancement: terrain funneling
        roughness = stats.get("terrain_roughness", 0.4)
        wind_enhance = 1.0 + roughness * 0.3
        score_val = max(orographic, flood_risk * 0.5)
        score_val = min(1.0, max(0.0, score_val))
        return {
            "score": round(score_val, 4),
            "mean_slope_deg": round(slope, 2),
            "ridge_orientation_deg": ridge_angle,
            "orographic_lift": round(orographic, 4),
            "valley_flood_risk": round(flood_risk, 4),
            "wind_enhancement": round(wind_enhance, 4),
            "available": True,
        }
