"""FIRE SIREN — owns RH + wind + soil. Watches red flag conditions."""

from __future__ import annotations

from typing import Any

from .base_siren import BaseSiren


class FireSiren(BaseSiren):
    name = "FIRE"

    def get_raw_signal(self, observation: dict, payload: dict) -> Any:
        rh = observation.get("humidity_pct")
        wind = observation.get("wind_speed_mph") or 0
        soil = (payload.get("flash_flood_fixture") or {}).get("soil_moisture")
        if soil is None:
            soil = payload.get("soil_moisture", 0.5)
        return (rh, wind, soil)

    def signal_to_status(self, raw_signal: Any, payload: dict | None = None) -> str:
        if raw_signal is None or not isinstance(raw_signal, (tuple, list)) or len(raw_signal) < 3:
            return "WATCHING"
        rh = float(raw_signal[0] or 50)
        wind = float(raw_signal[1] or 0)
        soil = float(raw_signal[2] or 0.5)
        if rh < 25 and wind > 15 and soil < 0.2:
            return "SCREAMING"
        if rh < 35 and wind > 10:
            return "ALERT"
        return "WATCHING"

    def check_veto(self, observation: dict, payload: dict, raw_status: str = "") -> bool:
        """Wet soil = no fire risk regardless of wind."""
        soil = (payload.get("flash_flood_fixture") or {}).get("soil_moisture")
        if soil is None:
            soil = payload.get("soil_moisture", 0.5)
        if soil is not None and float(soil) > 0.5:
            return True
        return False
