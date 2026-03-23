"""
GAIA Environmental Damage Engine
Scores how vulnerable the region already is before the next event arrives.
"""

from __future__ import annotations

from runtime.engines.common import clamp, month_key


class EnvironmentalEngine:
    def __init__(self):
        self.history = {}

    def ingest(self, station_id, timestamp, **data):
        self.history.setdefault(station_id, []).append({"timestamp": timestamp, **data})
        if len(self.history[station_id]) > 100:
            self.history[station_id] = self.history[station_id][-100:]

    def score(self, station_id="region", **current_data):
        recent_event = clamp(current_data.get("recent_event_severity", 0.0))
        precip_ratio = current_data.get("precip_7d_ratio", 0.0)
        soil_saturation = clamp(precip_ratio / 2.0)
        drought_raw = current_data.get("drought_class", 0)
        if isinstance(drought_raw, str) and drought_raw.upper().startswith("D"):
            drought_value = int(drought_raw[1:])
        else:
            drought_value = int(drought_raw or 0)
        drought_score = clamp(drought_value / 4.0)
        stream_score = clamp(current_data.get("stream_level_ratio", 0.0) / 1.5)
        month = month_key(current_data.get("timestamp"))
        seasonal = 0.0
        if month in {"nov", "dec", "jan", "feb"}:
            seasonal = 0.5 if current_data.get("frozen_ground") else 0.3
        elif month in {"mar", "apr", "may"}:
            seasonal = 0.4
        elif month in {"jun", "jul", "aug"}:
            seasonal = 0.35
        surface_ozone = current_data.get("surface_ozone_ppb")
        ozone_score = 0.0
        if surface_ozone is not None:
            ozone_score = clamp((surface_ozone - 30.0) / 40.0)

        channels = {
            "recent_event_history": recent_event,
            "soil_saturation_proxy": soil_saturation,
            "drought_status": drought_score,
            "stream_level_proxy": stream_score,
            "seasonal_vulnerability": seasonal,
            "surface_ozone": ozone_score,
        }
        weighted = (
            channels["recent_event_history"] * 0.30
            + channels["soil_saturation_proxy"] * 0.25
            + channels["drought_status"] * 0.15
            + channels["stream_level_proxy"] * 0.20
            + channels["seasonal_vulnerability"] * 0.10
        )
        return {"engine": "environmental", "score": round(clamp(weighted), 4), "channels": channels}

