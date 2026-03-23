"""
Mudslide Engine — East TN debris flow risk.

Steep slopes + saturated soil + heavy rain = debris flows.
High risk: sevier, blount, hawkins, grainger.
"""

from __future__ import annotations

from runtime.engines.terrain_engine import get_terrain_stats, COUNTY_CENTROIDS

HIGH_RISK_COUNTIES = {"sevier", "blount", "hawkins", "grainger"}


class MudslideEngine:
    def score(self, region: str, payload: dict | None = None, **kwargs) -> dict:
        payload = payload or {}
        stats = get_terrain_stats(region)
        slope_deg = stats.get("mean_slope_deg", 8.0)

        soil = float(payload.get("soil_moisture", 0.5) or 0.5)
        precip_rate = float(payload.get("precip_rate_in_hr", 0) or payload.get("rainfall_rate_in_hr", 0) or 0)

        slope_factor = min(1.0, slope_deg / 45.0)
        soil_factor = soil
        rain_factor = min(1.0, precip_rate / 2.0)

        mudslide_score = slope_factor * soil_factor * rain_factor * 3
        mudslide_score = min(mudslide_score, 1.0)

        if soil >= 0.9 and slope_deg > 20 and precip_rate > 0.5:
            mudslide_score = max(mudslide_score, 0.85)

        alerts = []
        if mudslide_score > 0.8:
            alerts.append("DEBRIS_FLOW_WARNING")
        elif mudslide_score > 0.5:
            alerts.append("DEBRIS_FLOW_WATCH")

        return {
            "score": round(mudslide_score, 4),
            "slope_factor": round(slope_factor, 4),
            "soil_factor": round(soil_factor, 4),
            "rain_factor": round(rain_factor, 4),
            "alerts": alerts,
        }
