"""
GAIA Engine 14: SIREN — Storm Infrasound & Resonance Engine

Reads the storm's acoustic precursors through proxy signals derived
from existing ASOS data. Every severe weather event produces a unique
frequency signature that begins BEFORE the event is visible.

Named for the ancient Greek Sirens — beings whose song warned of
danger ahead. GAIA's Siren warns of storms.

Tier 1 channels (ASOS-derived, available now):
  - Pressure oscillation variance
  - Thunder precursor timing
  - Gust coherence
  - Pressure-visibility divergence
  - Sound propagation anomaly

Tier 2 channels (future data connections):
  - Lightning flash rate + collapse detection
  - Radar-derived rotation proxy

The key insight: when the storm's song is ABSENT but surface
conditions are loaded, the event is unlikely to fire. This is
the false alarm discriminator GAIA has been missing.

© 2026 Jennifer Leigh West | The Forgotten Code Research Institute
Protected under U.S. Copyright Registration No. 1-14949237971
"""

from __future__ import annotations

import math
import logging
from collections import deque

logger = logging.getLogger(__name__)

# The Frozen Core — atmospheric acoustics
SOUND_SPEED_AT_20C = 343.0   # m/s in dry air at 20°C
SOUND_SPEED_COEFF_T = 0.6    # m/s per °C
SOUND_SPEED_COEFF_H = 0.0015 # fractional increase per % RH


def calculate_sound_speed(temp_c: float, humidity_pct: float) -> float:
    """
    Speed of sound as a function of temperature and humidity.

    The ancients read this with their bodies: "sound carries further
    before rain" = faster sound speed in warm humid air under inversion.
    """
    v = SOUND_SPEED_AT_20C + SOUND_SPEED_COEFF_T * (temp_c - 20.0)
    v *= (1.0 + SOUND_SPEED_COEFF_H * max(humidity_pct, 0.0))
    return v


def gaia_obs_to_siren_obs(obs: dict) -> dict:
    """
    Convert GAIA ASOS observation format to Siren engine format.
    """
    temp_f = obs.get("temperature_f")
    temp_c = ((temp_f - 32.0) * 5.0 / 9.0) if temp_f is not None else None

    pressure_mb = obs.get("pressure_mb")
    # 1 mb = 0.02953 inHg
    altimeter_inhg = (pressure_mb * 0.02953) if pressure_mb is not None else None

    wind_mph = obs.get("wind_speed_mph") or 0
    gust_mph = obs.get("wind_gust_mph") or wind_mph
    # 1 mph = 0.868976 kt
    wind_sustained_kt = wind_mph * 0.868976
    wind_gust_kt = gust_mph * 0.868976 if gust_mph else wind_sustained_kt

    vis = obs.get("visibility_mi")
    visibility_sm = float(vis) if vis is not None else None

    # pressure_trend_hpa_hr: numeric rate (hPa/hr), negative = falling. From channel_context.
    # Fallback: pressure_trend categorical ("falling" -> -1.5, "falling_fast" -> -3.0)
    ptr = obs.get("pressure_trend_hpa_hr")
    if ptr is not None and isinstance(ptr, (int, float)):
        pressure_trend_hpa_hr = float(ptr)
    elif obs.get("pressure_trend") == "falling_fast":
        pressure_trend_hpa_hr = -3.0
    elif obs.get("pressure_trend") == "falling":
        pressure_trend_hpa_hr = -1.5
    else:
        pressure_trend_hpa_hr = 0.0

    text = " ".join(
        str(obs.get(f, "") or "").lower()
        for f in ("text_description", "metar", "present_weather")
    )
    has_thunder = "thunder" in text or " ts" in f" {text} " or text.startswith("ts")

    return {
        "altimeter_inhg": altimeter_inhg,
        "temperature_c": temp_c,
        "humidity_pct": obs.get("humidity_pct"),
        "wind_sustained_kt": wind_sustained_kt,
        "wind_gust_kt": wind_gust_kt,
        "visibility_sm": visibility_sm,
        "pressure_trend_hpa_hr": pressure_trend_hpa_hr,
        "has_thunder": has_thunder,
        "thunder_onset_minutes": None,
        "lightning_flash_rate": obs.get("lightning_flash_rate"),
        "mesocyclone_strength": obs.get("mesocyclone_strength"),
    }


class SirenEngine:
    """
    Storm Infrasound & Resonance Engine.

    Scores the atmospheric acoustic state from 0.0 (silent) to 1.0
    (confirmed storm song). Uses proxy signals from standard ASOS
    observations to detect the precursor frequencies that begin
    before severe weather becomes visible.
    """

    DEFAULTS = {
        "pressure_oscillation_window_min": 30,
        "pressure_oscillation_warn": 0.020,  # East TN has more baseline variation
        "pressure_oscillation_max": 0.060,
        "gust_factor_warn": 1.8,  # ETN mountain terrain has gusty baseline
        "gust_factor_max": 3.0,
        "gust_trend_window": 6,
        "divergence_pressure_threshold": -1.0,
        "divergence_vis_improving": 0.0,
        "divergence_max": 5.0,
        "sound_baseline_speed": 350.0,  # East TN typical (348-352 m/s with humidity)
        "sound_anomaly_warn": 5.0,  # Normal seasonal variation is wider
        "sound_anomaly_max": 12.0,
        "thunder_precursor_score": 0.7,
        "flash_accel_max": 20.0,
        "flash_collapse_ratio": 0.5,
        "flash_collapse_window": 6,
        "min_channels_for_boost": 3,
        "convergence_boost": 1.2,
    }

    def __init__(self, config: dict | None = None):
        self.config = {**self.DEFAULTS}
        if config:
            self.config.update(config)

        self.pressure_history: deque = deque(maxlen=60)
        self.gust_factor_history: deque = deque(maxlen=30)
        self.visibility_history: deque = deque(maxlen=30)
        self.flash_rate_history: deque = deque(maxlen=20)
        self.sound_speed_history: deque = deque(maxlen=30)
        self.channels: dict = {}
        self.metadata: dict = {}

    def ingest(self, station_id: str, timestamp: str, **data: object) -> None:
        """GAIA compatibility: forward to score with converted obs."""
        obs = {"station_id": station_id, "timestamp": timestamp, **data}
        siren_obs = gaia_obs_to_siren_obs(obs)
        self.score(siren_obs)

    def score(self, observation: dict) -> float:
        """
        Score the atmospheric acoustic state.

        observation : dict
            GAIA format (station_id, timestamp, pressure_mb, ...) or
            Siren format (altimeter_inhg, temperature_c, ...).
            If keys look like GAIA format, auto-convert.
        """
        if "pressure_mb" in observation and "altimeter_inhg" not in observation:
            observation = gaia_obs_to_siren_obs(observation)

        self.channels = {
            "pressure_oscillation": 0.0,
            "thunder_precursor": 0.0,
            "gust_coherence": 0.0,
            "pressure_vis_divergence": 0.0,
            "sound_propagation": 0.0,
            "lightning_flash_rate": 0.0,
            "rotation_proxy": 0.0,
        }
        self.metadata = {}
        active_channels = 0

        alt = observation.get("altimeter_inhg")
        if alt is not None:
            self.pressure_history.append(alt)
            if len(self.pressure_history) >= self.config["pressure_oscillation_window_min"]:
                window = list(self.pressure_history)[
                    -self.config["pressure_oscillation_window_min"]:
                ]
                mean_p = sum(window) / len(window)
                variance = sum((x - mean_p) ** 2 for x in window) / len(window)
                if variance > self.config["pressure_oscillation_warn"]:
                    self.channels["pressure_oscillation"] = min(
                        1.0, variance / self.config["pressure_oscillation_max"]
                    )
                    active_channels += 1
                self.metadata["pressure_variance_inhg2"] = round(variance, 6)

        if observation.get("has_thunder"):
            onset = observation.get("thunder_onset_minutes")
            if onset is not None and onset < 60:
                self.channels["thunder_precursor"] = self.config["thunder_precursor_score"]
                active_channels += 1
            elif onset is None:
                self.channels["thunder_precursor"] = 0.5
                active_channels += 1

        sustained = observation.get("wind_sustained_kt", 0)
        gust = observation.get("wind_gust_kt", 0)
        if sustained > 0:
            gust_factor = max(gust, sustained) / max(sustained, 1)
            self.gust_factor_history.append(gust_factor)
            if len(self.gust_factor_history) >= 3:
                recent = list(self.gust_factor_history)
                gust_trend = (recent[-1] - recent[0]) / max(len(recent), 1)
                if gust_factor > self.config["gust_factor_warn"] and gust_trend > 0:
                    raw = (gust_factor - 1.0) / (
                        self.config["gust_factor_max"] - 1.0
                    )
                    self.channels["gust_coherence"] = min(1.0, raw)
                    active_channels += 1
                    self.metadata["gust_factor"] = round(gust_factor, 2)
                    self.metadata["gust_trend"] = round(gust_trend, 4)

        pressure_trend = observation.get("pressure_trend_hpa_hr", 0)
        vis = observation.get("visibility_sm")
        if vis is not None:
            self.visibility_history.append(vis)
        if (
            pressure_trend < self.config["divergence_pressure_threshold"]
            and len(self.visibility_history) >= 3
        ):
            vis_list = list(self.visibility_history)
            vis_trend = (vis_list[-1] - vis_list[0]) / max(len(vis_list), 1)
            if vis_trend > self.config["divergence_vis_improving"]:
                divergence = abs(pressure_trend) * max(vis_trend, 0.1)
                self.channels["pressure_vis_divergence"] = min(
                    1.0, divergence / self.config["divergence_max"]
                )
                active_channels += 1
                self.metadata["divergence_value"] = round(divergence, 3)

        temp = observation.get("temperature_c")
        hum = observation.get("humidity_pct")
        if temp is not None and hum is not None:
            local_speed = calculate_sound_speed(temp, hum)
            self.sound_speed_history.append(local_speed)
            anomaly = local_speed - self.config["sound_baseline_speed"]
            if anomaly > self.config["sound_anomaly_warn"]:
                self.channels["sound_propagation"] = min(
                    1.0, anomaly / self.config["sound_anomaly_max"]
                )
                active_channels += 1
            self.metadata["sound_speed_ms"] = round(local_speed, 1)
            self.metadata["sound_anomaly_ms"] = round(anomaly, 1)

        flash_rate = observation.get("lightning_flash_rate")
        if flash_rate is not None:
            self.flash_rate_history.append(flash_rate)
            if len(self.flash_rate_history) >= 4:
                rates = list(self.flash_rate_history)
                if len(rates) >= 2:
                    accel = rates[-1] - rates[-2]
                    if accel > 0:
                        self.channels["lightning_flash_rate"] = min(
                            1.0, accel / self.config["flash_accel_max"]
                        )
                        active_channels += 1
                if self._detect_flash_collapse():
                    self.channels["lightning_flash_rate"] = 0.95
                    active_channels += 2
                    self.metadata["flash_collapse_detected"] = True

        meso = observation.get("mesocyclone_strength")
        if meso is not None and meso > 0:
            self.channels["rotation_proxy"] = min(1.0, meso)
            active_channels += 1

        if active_channels == 0:
            return 0.0

        channel_sum = sum(self.channels.values())
        score = channel_sum / max(active_channels, 3)
        if active_channels >= self.config["min_channels_for_boost"]:
            score = min(1.0, score * self.config["convergence_boost"])

        self.metadata["active_channels"] = active_channels
        self.metadata["channel_scores"] = dict(self.channels)
        return round(score, 4)

    def _detect_flash_collapse(self) -> bool:
        rates = list(self.flash_rate_history)
        window = self.config["flash_collapse_window"]
        if len(rates) < window:
            return False
        recent = rates[-2:]
        prior = rates[-window:-2]
        if not prior or max(prior) == 0:
            return False
        recent_avg = sum(recent) / len(recent)
        prior_avg = sum(prior) / len(prior)
        if prior_avg == 0:
            return False
        return (recent_avg / prior_avg) < self.config["flash_collapse_ratio"]

    def get_evidence(self) -> dict:
        return {
            "engine": "siren",
            "channels": dict(self.channels),
            "metadata": dict(self.metadata),
        }

    def reset(self) -> None:
        self.pressure_history.clear()
        self.gust_factor_history.clear()
        self.visibility_history.clear()
        self.flash_rate_history.clear()
        self.sound_speed_history.clear()
        self.channels = {}
        self.metadata = {}
