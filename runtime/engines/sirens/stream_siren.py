"""STREAM SIREN — owns USGS streamflow rise rate. Watches fast stream rise."""

from __future__ import annotations

from typing import Any

from .base_siren import BaseSiren


class StreamSiren(BaseSiren):
    name = "STREAM"

    def get_raw_signal(self, observation: dict, payload: dict) -> Any:
        ff = payload.get("flash_flood_fixture") or {}
        return ff.get("rise_rate_ft_hr") or ff.get("stream_rise_rate")

    def signal_to_status(self, raw_signal: Any, payload: dict | None = None) -> str:
        if raw_signal is None:
            return "WATCHING"
        v = float(raw_signal)
        if v > 0.8:
            return "SCREAMING"
        if v > 0.3:
            return "ALERT"
        stage = getattr(self, "_stage_ratio", None)
        if stage is not None and stage < 0.3:
            return "SILENT"
        return "WATCHING"

    def check_veto(self, observation: dict, payload: dict, raw_status: str = "") -> bool:
        """Rising stream without rain = dam release, not flash flood."""
        precip = sum((o.get("precip_1h_in") or 0) for o in payload.get("station_observations", []))
        window = payload.get("precip_72hr_mm") or 0
        if precip == 0 and (window or 0) < 1:
            return True
        return False
