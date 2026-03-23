"""MOISTURE SIREN — owns t_td_crossover_velocity. Watches moisture convergence vs divergence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .base_siren import BaseSiren, SirenResult, SirenAudit


class MoistureSiren(BaseSiren):
    name = "MOISTURE"

    def get_raw_signal(self, observation: dict, payload: dict) -> Any:
        return observation.get("t_td_crossover_velocity")

    def signal_to_status(self, raw_signal: Any, payload: dict | None = None) -> str:
        if raw_signal is None:
            return "WATCHING"
        v = float(raw_signal)
        # Seasonal sensitivity: summer 0.8 = harder to alert (-1.0/0.8=-1.25), winter 0 = off
        factor = 1.0
        if payload:
            profile = payload.get("seasonal_profile") or {}
            sens = profile.get("siren_sensitivity", 1.0)
            if sens <= 0:
                return "WATCHING"  # Winter: convective sirens off
            factor = max(0.5, sens)
        alert_thresh = -1.0 / factor
        scream_thresh = -2.0 / factor
        if v < scream_thresh:
            return "SCREAMING"
        if v < alert_thresh:
            return "ALERT"
        if v > 0.2:
            return "SILENT"
        return "WATCHING"

    def evaluate(self, observation: dict, payload: dict, other_siren_states: dict) -> SirenResult:
        """Override: data quality short-circuit returns WATCHING."""
        if self._data_quality_veto(observation, payload):
            return SirenResult(
                status="WATCHING",
                confidence=0.0,
                audit=SirenAudit(
                    siren_name=self.name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    raw_signal_value=observation.get("t_td_crossover_velocity"),
                    raw_status="WATCHING",
                    confidence_score=0.0,
                    veto_checked=True,
                    veto_triggered=True,
                    corroboration_available=False,
                    final_status="WATCHING",
                    reason="Data quality: stale or insufficient history",
                ),
            )
        return super().evaluate(observation, payload, other_siren_states)

    def check_veto(self, observation: dict, payload: dict, raw_status: str = "") -> bool:
        """Cannot scream/alert if no column moisture, extreme heat, or winter marginal signal."""
        # Precipitable water < 15mm: no severe convection
        station_obs = payload.get("station_observations", [{}])
        gps_pw = (station_obs[0] if station_obs else {}).get("gps_pw")
        precipitable = observation.get("precipitable_water_in") or (float(gps_pw or 0) * 50)
        if precipitable is not None and float(precipitable) < 15:
            return True
        # Extreme heat: dry air, not storm moisture
        temp_f = observation.get("temperature_f")
        if temp_f is not None and float(temp_f) > 95:
            return True
        # Winter: require v < -1.5 for ALERT (dewpoint changes not storm precursors)
        ts = observation.get("timestamp", "") or payload.get("timestamp", "")
        month = self._month_from_timestamp(ts)
        if month in (12, 1, 2) and raw_status == "ALERT":
            v = observation.get("t_td_crossover_velocity")
            if v is not None and -1.5 <= float(v) < -1.0:
                return True
        return False

    def _data_quality_veto(self, observation: dict, payload: dict) -> bool:
        """Return True if data too stale or insufficient history."""
        age = self._data_age_minutes(observation, payload)
        if age > 90:
            return True
        min_obs = 1 if payload.get("event_type") in ("heavy_snow", "winter_storm") else 3
        if self._observation_count(payload) < min_obs:
            return True
        return False

    def _data_age_minutes(self, observation: dict, payload: dict) -> float:
        try:
            ref_ts = payload.get("timestamp") or observation.get("timestamp", "")
            obs_ts = observation.get("timestamp", "")
            if not ref_ts or not obs_ts:
                return 0.0
            ref = datetime.fromisoformat(ref_ts.replace("Z", "+00:00"))
            obs = datetime.fromisoformat(obs_ts.replace("Z", "+00:00"))
            return abs((ref - obs).total_seconds()) / 60.0
        except (ValueError, TypeError):
            return 0.0

    def _observation_count(self, payload: dict) -> int:
        if "observation_count" in payload:
            return int(payload.get("observation_count", 0))
        obs = payload.get("observations") or payload.get("station_observations") or []
        return len(obs) if obs else 999

    def _month_from_timestamp(self, ts: str) -> int:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.month
        except (ValueError, TypeError):
            return 0
