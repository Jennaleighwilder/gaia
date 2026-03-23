"""LIGHTNING SIREN — owns GLM flash rate. Watches lightning increase."""

from __future__ import annotations

from typing import Any

from .base_siren import BaseSiren


class LightningSiren(BaseSiren):
    name = "LIGHTNING"

    def get_raw_signal(self, observation: dict, payload: dict) -> Any:
        return observation.get("lightning_flash_rate") or 0

    def signal_to_status(self, raw_signal: Any, payload: dict | None = None) -> str:
        if raw_signal is None:
            return "WATCHING"
        r = float(raw_signal)
        if r > 50:
            return "SCREAMING"
        if r > 10:
            return "ALERT"
        if r == 0:
            return "SILENT"
        return "WATCHING"

    def check_veto(self, observation: dict, payload: dict, raw_status: str = "") -> bool:
        """Lightning without moisture = dry lightning, different threat. TPW < 20mm."""
        obs = (payload.get("station_observations") or [observation])[0]
        pw = obs.get("precipitable_water_in") or observation.get("precipitable_water_in")
        if pw is not None:
            pw_mm = float(pw) * 25.4
        else:
            gps = obs.get("gps_pw") or observation.get("gps_pw")
            pw_mm = float(gps or 0) * 50
        if pw_mm < 20:
            return True
        return False
