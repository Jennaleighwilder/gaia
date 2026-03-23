"""
SMAP Soil Moisture Engine — Tier 1

Daily soil moisture 0-1. Flash flood / fire / mudslide multipliers.
Source: NASA Earthdata SMAP (requires auth).
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
SOIL_CACHE = ROOT / "data" / "soil"


def _get_soil_moisture_cached(region: str, date_str: str) -> dict | None:
    """Return cached soil data or None."""
    if not SOIL_CACHE.exists():
        return None
    path = SOIL_CACHE / f"{region}_{date_str[:7]}.json"
    if not path.exists():
        return None
    try:
        import json
        return json.loads(path.read_text())
    except Exception:
        return None


class SoilEngine:
    """Tier 1: Soil moisture, flash flood / fire / mudslide risk."""

    def __init__(self):
        self.history = {}

    def ingest(self, region: str, timestamp: str, **data) -> None:
        self.history.setdefault(region, []).append({"timestamp": timestamp, **data})
        if len(self.history[region]) > 7:
            self.history[region] = self.history[region][-7:]

    def score(self, region: str, payload: dict | None = None, **kwargs) -> dict:
        payload = payload or {}
        date_str = (payload.get("timestamp") or "")[:10] or "2024-01-01"
        soil_data = payload.get("soil_fixture") or _get_soil_moisture_cached(region, date_str)
        if soil_data is None:
            return {
                "score": 0.0,
                "soil_moisture": None,
                "saturation_trend": None,
                "flash_flood_certain": False,
                "fire_risk": False,
                "mudslide_risk": False,
                "available": False,
            }
        moisture = soil_data.get("soil_moisture")
        if moisture is None:
            return {"score": 0.0, "soil_moisture": None, "available": False, **{k: False for k in ["flash_flood_certain", "fire_risk", "mudslide_risk"]}}
        trend = soil_data.get("saturation_trend", "stable")
        rainfall = payload.get("rainfall_rate_in_hr") or 0.0
        wind_speed = payload.get("wind_speed_mph") or 0.0
        slope = payload.get("terrain_slope_deg") or 10.0
        flash_flood = moisture >= 0.8 and rainfall >= 0.5
        fire_risk = moisture <= 0.2 and wind_speed >= 15
        mudslide = moisture >= 0.9 and slope >= 15
        score_val = 0.2 + 0.6 * moisture if moisture else 0.0
        score_val = min(1.0, max(0.0, score_val))
        return {
            "score": round(score_val, 4),
            "soil_moisture": round(moisture, 4),
            "saturation_trend": trend,
            "flash_flood_certain": flash_flood,
            "fire_risk": fire_risk,
            "mudslide_risk": mudslide,
            "available": True,
        }
