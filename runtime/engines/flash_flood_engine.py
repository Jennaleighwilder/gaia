"""
Flash Flood Engine — East TN terrain-driven flood detection.

Rain on saturated slopes + narrow valleys = deadly in under an hour.
Runs on parallel decision track: FLASH_FLOOD_WARNING independent of severe weather.
"""

from __future__ import annotations

from runtime.engines.common import clamp


class FlashFloodEngine:
    """Terrain-driven flash flood signals for East TN."""

    def __init__(self):
        self.history = {}

    def ingest(self, region: str, timestamp: str, **data) -> None:
        self.history.setdefault(region, []).append({"timestamp": timestamp, **data})
        if len(self.history[region]) > 24:
            self.history[region] = self.history[region][-24:]

    def score(self, region: str, payload: dict | None = None, **kwargs) -> dict:
        payload = payload or {}
        score = 0.0
        reasons: list[str] = []

        # Hydrological: stream stage ratio, rise rate
        hydro = payload.get("hydrological") or {}
        if isinstance(hydro, dict):
            stage_ratio = float(hydro.get("stage_ratio", 0) or hydro.get("stream_stage_vs_flood_ratio", 0))
            rise_rate = float(hydro.get("rise_rate_ft_hr", 0) or 0)
        else:
            stage_ratio = 0.0
            rise_rate = 0.0
        if stage_ratio > 0.8 and rise_rate > 0.3:
            score += 0.4
            reasons.append("stream_rising")
        elif stage_ratio > 0.6 and rise_rate > 0.1:
            score += 0.2
        elif stage_ratio > 0.5:
            score += 0.1

        # Soil moisture
        soil = float(payload.get("soil_moisture", 0.5) or 0.5)
        soil_detail = payload.get("soil_fixture") or {}
        if isinstance(soil_detail, dict) and "soil_moisture" in soil_detail:
            soil = float(soil_detail.get("soil_moisture", soil))
        if soil >= 0.85:
            score += 0.3
            reasons.append("soil_saturated")
        elif soil > 0.7:
            score += 0.15

        # Terrain valley risk
        terrain = payload.get("terrain") or {}
        if isinstance(terrain, dict):
            valley_risk = float(terrain.get("valley_flood_risk", 0) or 0)
        else:
            valley_risk = 0.0
        # Also from engine_details.terrain
        terrain_detail = payload.get("_terrain_detail") or {}
        valley_risk = valley_risk or float(terrain_detail.get("valley_flood_risk", 0) or 0)
        if valley_risk >= 0.7:
            score += 0.2
            reasons.append("terrain_funnel")
        elif valley_risk > 0.5:
            score += 0.1

        # Antecedent rainfall 72hr
        precip_72hr = float(payload.get("precip_72hr_mm", 0) or 0)
        if precip_72hr > 75:
            score += 0.3
            reasons.append("antecedent_wet")
        elif precip_72hr > 50:
            score += 0.15
        elif precip_72hr > 25:
            score += 0.05

        # Current rainfall rate (in/hr)
        precip_rate = float(payload.get("precip_rate_in_hr", 0) or payload.get("rainfall_rate_in_hr", 0) or 0)
        if precip_rate > 1.0:
            score += 0.4
            reasons.append("intense_rainfall")
        elif precip_rate > 0.5:
            score += 0.2
        elif precip_rate > 0.25:
            score += 0.1

        # Atmospheric river — TPW > 50mm, moisture surge from Gulf/Atlantic
        atmospheric_river = bool(payload.get("atmospheric_river_detected", False))
        if atmospheric_river and valley_risk > 0.5:
            score += 0.25
            reasons.append("atmospheric_river")
        if atmospheric_river and valley_risk > 0.7 and (soil > 0.7 or precip_72hr > 50):
            score = max(score, 0.92)
            reasons.append("AR_TERRAIN_EXTREME")

        # Atmospheric proxies for precipitation (ASOS gauge may miss local rain)
        dewpoint_depression = float(payload.get("dewpoint_depression_f") or 99)
        pressure_change = float(payload.get("pressure_change_mb") or 0)
        atmosphere_wet = dewpoint_depression <= 3.0
        atmosphere_unstable = pressure_change >= 3.0

        # FLASH FLOOD CERTAIN
        if soil >= 0.85 and valley_risk >= 0.7 and precip_rate > 0.5:
            score = max(score, 0.95)
            reasons.append("FLASH_FLOOD_CERTAIN")
        elif soil >= 0.85 and valley_risk >= 0.7 and precip_72hr > 50:
            score = max(score, 0.9)
            reasons.append("FLASH_FLOOD_LIKELY")
        elif soil >= 0.85 and valley_risk >= 0.7 and (atmosphere_wet or atmosphere_unstable):
            score = max(score, 0.9)
            if atmosphere_wet:
                reasons.append("SATURATED_AIR_FLOOD_LIKELY")
            if atmosphere_unstable:
                reasons.append("PRESSURE_DROP_FLOOD_LIKELY")

        score = clamp(min(score, 1.0))
        return {
            "score": round(score, 4),
            "flash_flood_certain": score >= 0.9,
            "reasons": reasons,
            "stage_ratio": round(stage_ratio, 4),
            "soil_moisture": round(soil, 4),
            "valley_risk": round(valley_risk, 4),
            "precip_72hr_mm": round(precip_72hr, 2),
            "precip_rate_in_hr": round(precip_rate, 4),
            "atmospheric_river_detected": atmospheric_river,
        }
