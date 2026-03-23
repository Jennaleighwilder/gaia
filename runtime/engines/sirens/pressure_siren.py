"""PRESSURE SIREN — owns pressure_acceleration + pressure_trend. Watches accelerating pressure drop."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .base_siren import BaseSiren, SirenResult, SirenAudit


class PressureSiren(BaseSiren):
    name = "PRESSURE"

    def get_raw_signal(self, observation: dict, payload: dict) -> Any:
        p_accel = observation.get("pressure_acceleration")
        p_trend = observation.get("pressure_trend_hpa_hr")
        return (p_accel, p_trend)

    def signal_to_status(self, raw_signal: Any, payload: dict | None = None) -> str:
        if raw_signal is None or not isinstance(raw_signal, (tuple, list)) or len(raw_signal) < 2:
            return "WATCHING"
        p_accel = float(raw_signal[0] or 0)
        p_trend = float(raw_signal[1] or 0)
        # Seasonal sensitivity: summer 0.8 = harder (0.2/0.8=0.25), winter 0 = off
        factor = 1.0
        if payload:
            profile = payload.get("seasonal_profile") or {}
            sens = profile.get("siren_sensitivity", 1.0)
            if sens <= 0:
                return "WATCHING"  # Winter: convective sirens off
            factor = max(0.5, sens)
        alert_thresh = 0.2 / factor
        scream_accel = 0.4 / factor
        scream_trend = -0.6
        if p_accel > scream_accel and p_trend < scream_trend:
            return "SCREAMING"
        if p_accel > alert_thresh:
            return "ALERT"
        if p_accel < -0.15:
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
                    raw_signal_value=self.get_raw_signal(observation, payload),
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
        """No flow, rising pressure, or single spike = veto."""
        # Wind < 5mph: pressure change is thermal not dynamic
        wind = observation.get("wind_speed_mph")
        if wind is not None and float(wind) < 5.0:
            return True
        # Rising pressure: no storm development
        p_trend = observation.get("pressure_trend_hpa_hr")
        if p_trend is not None and float(p_trend) > 0:
            return True
        # Consecutive obs: require 2+ with signal (single spike is noise)
        if raw_status in ("ALERT", "SCREAMING"):
            if len(self.signal_history) < 1:
                return True
            last_status = self.signal_history[-1][1]
            if last_status not in ("ALERT", "SCREAMING"):
                return True
        return False

    def _data_quality_veto(self, observation: dict, payload: dict) -> bool:
        if self._data_age_minutes(observation, payload) > 90:
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
