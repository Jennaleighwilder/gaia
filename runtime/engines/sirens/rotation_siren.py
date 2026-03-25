"""ROTATION SIREN — owns radar velocity couplet. Watches rotation in radar."""

from __future__ import annotations

from typing import Any

from .base_siren import BaseSiren


class RotationSiren(BaseSiren):
    name = "ROTATION"

    def get_raw_signal(self, observation: dict, payload: dict) -> Any:
        radar = payload.get("radar_fixture") or {}
        couplet = radar.get("rotation_couplet_kt")
        if couplet is not None:
            return couplet
        return radar.get("velocity_max")

    def signal_to_status(self, raw_signal: Any, payload: dict | None = None) -> str:
        if raw_signal is None:
            return "WATCHING"
        v = float(raw_signal)
        if v > 0.7:
            return "SCREAMING"
        if v > 0.4:
            return "ALERT"
        return "WATCHING"

    def check_veto(self, observation: dict, payload: dict, raw_status: str = "") -> bool:
        """Rotation without storm = data artifact."""
        radar = payload.get("radar_fixture") or {}
        refl = radar.get("composite_reflectivity")
        if refl is not None and float(refl) < 35:
            return True
        return False
