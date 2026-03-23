"""MOISTURE COLUMN SIREN — owns GPS-PW / GOES TPW. Watches column loading."""

from __future__ import annotations

from typing import Any

from .base_siren import BaseSiren


class ColumnSiren(BaseSiren):
    name = "COLUMN"

    def get_raw_signal(self, observation: dict, payload: dict) -> Any:
        pw_in = observation.get("precipitable_water_in")
        if pw_in is not None:
            return float(pw_in) * 25.4  # in to mm
        gps = observation.get("gps_pw")
        if gps is not None:
            return float(gps) * 50  # 0-1 score -> rough mm
        return None

    def signal_to_status(self, raw_signal: Any, payload: dict | None = None) -> str:
        if raw_signal is None:
            return "WATCHING"
        v = float(raw_signal)
        if v > 45:
            return "SCREAMING"
        if v > 30:
            return "ALERT"
        if v < 15:
            return "SILENT"
        return "WATCHING"

    def check_veto(self, observation: dict, payload: dict, raw_status: str = "") -> bool:
        return False
