"""SOIL SIREN — owns soil moisture. Watches saturation."""

from __future__ import annotations

from typing import Any

from .base_siren import BaseSiren


class SoilSiren(BaseSiren):
    name = "SOIL"

    def get_raw_signal(self, observation: dict, payload: dict) -> Any:
        ff = payload.get("flash_flood_fixture") or {}
        return ff.get("soil_moisture") or payload.get("soil_moisture")

    def signal_to_status(self, raw_signal: Any, payload: dict | None = None) -> str:
        if raw_signal is None:
            return "WATCHING"
        v = float(raw_signal)
        if v > 0.90:
            return "SCREAMING"
        if v > 0.70:
            return "ALERT"
        if v < 0.30:
            return "SILENT"
        return "WATCHING"

    def check_veto(self, observation: dict, payload: dict, raw_status: str = "") -> bool:
        """Saturated soil without recent rain = irrigation or data error."""
        precip_72 = payload.get("precip_72hr_mm") or 0
        if precip_72 < 1:
            return True
        return False
