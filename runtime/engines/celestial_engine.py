"""
GAIA Engine 15: CELESTIAL — Space Weather Forcing Engine

Reads Level 1 of the atmospheric signal chain: solar and geomagnetic
activity that modulates terrestrial weather from above. Space weather
precursors arrive HOURS TO DAYS before terrestrial effects manifest.

Data sources (all free, all real-time, all NOAA SWPC):
  - Kp index (planetary geomagnetic index, 0-9)
  - Solar wind speed + density
  - IMF Bz component (negative = energy coupling)
  - GOES proton flux
  - G-scale storm alerts

The discriminator: when Celestial is LOW and surface engines are HIGH,
the atmosphere is loaded but nobody's pushing it. Probably false alarm.
When Celestial is HIGH and surface engines are HIGH, external forcing
confirms the threat. Real event.

© 2026 Jennifer Leigh West | The Forgotten Code Research Institute
Protected under U.S. Copyright Registration No. 1-14949237971
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

SWPC_URLS = {
    "kp_index": "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
    "solar_wind_plasma": "https://services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json",
    "solar_wind_mag": "https://services.swpc.noaa.gov/products/solar-wind/mag-7-day.json",
    "proton_flux": "https://services.swpc.noaa.gov/json/goes/primary/integral-protons-1-day.json",
    "alerts": "https://services.swpc.noaa.gov/products/alerts.json",
}


class CelestialEngine:
    """
    Space Weather Forcing Engine.

    Scores the solar-terrestrial forcing state from 0.0 (quiet sun)
    to 1.0 (major geomagnetic storm, strong terrestrial coupling).
    """

    DEFAULTS = {
        "kp_quiet": 2,
        "kp_unsettled": 3,
        "kp_minor_storm": 5,
        "kp_moderate_storm": 6,
        "kp_strong_storm": 7,
        "kp_severe_storm": 8,
        "kp_extreme_storm": 9,
        "sw_speed_normal": 400,
        "sw_speed_elevated": 500,
        "sw_speed_storm": 600,
        "sw_speed_extreme": 800,
        "sw_density_elevated": 10,
        "sw_density_storm": 20,
        "bz_coupling_weak": -3,
        "bz_coupling_moderate": -5,
        "bz_coupling_strong": -10,
        "bz_coupling_extreme": -20,
        "proton_s1": 10,
        "proton_s2": 100,
        "proton_s3": 1000,
        "weight_kp": 0.35,
        "weight_solar_wind": 0.25,
        "weight_bz": 0.25,
        "weight_proton": 0.15,
        "kp_trend_window": 8,
        "fetch_timeout_seconds": 10,
    }

    def __init__(self, config: dict | None = None, fetcher: object = None):
        self.config = {**self.DEFAULTS}
        if config:
            self.config.update(config)
        self.fetcher = fetcher
        self.channels: dict = {}
        self.metadata: dict = {}
        self._cache: dict = {}
        self._cache_expiry: dict = {}
        self._cache_ttl_seconds = 900

    def score(self, observation: dict | None = None) -> float:
        """
        Score the current space weather forcing state.

        observation : dict, optional
            Pre-fetched data for backtest: kp_index, solar_wind_speed_kms,
            solar_wind_density_pcm3, imf_bz_nt, proton_flux_pfu.
        """
        self.channels = {
            "kp_index": 0.0,
            "solar_wind": 0.0,
            "imf_bz": 0.0,
            "proton_flux": 0.0,
        }
        self.metadata = {}

        kp = self._get_value(observation, "kp_index", self._fetch_kp)
        sw_speed = self._get_value(observation, "solar_wind_speed_kms", self._fetch_sw_speed)
        sw_density = self._get_value(observation, "solar_wind_density_pcm3", self._fetch_sw_density)
        bz = self._get_value(observation, "imf_bz_nt", self._fetch_bz)
        proton = self._get_value(observation, "proton_flux_pfu", self._fetch_proton)

        if kp is not None:
            self.metadata["kp_index"] = kp
            if kp >= self.config["kp_extreme_storm"]:
                self.channels["kp_index"] = 1.0
                self.metadata["kp_class"] = "G5_EXTREME"
            elif kp >= self.config["kp_severe_storm"]:
                self.channels["kp_index"] = 0.9
                self.metadata["kp_class"] = "G4_SEVERE"
            elif kp >= self.config["kp_strong_storm"]:
                self.channels["kp_index"] = 0.75
                self.metadata["kp_class"] = "G3_STRONG"
            elif kp >= self.config["kp_moderate_storm"]:
                self.channels["kp_index"] = 0.6
                self.metadata["kp_class"] = "G2_MODERATE"
            elif kp >= self.config["kp_minor_storm"]:
                self.channels["kp_index"] = 0.45
                self.metadata["kp_class"] = "G1_MINOR"
            elif kp >= self.config["kp_unsettled"]:
                self.channels["kp_index"] = 0.2
                self.metadata["kp_class"] = "UNSETTLED"
            else:
                self.channels["kp_index"] = 0.0
                self.metadata["kp_class"] = "QUIET"

        if sw_speed is not None:
            self.metadata["sw_speed_kms"] = sw_speed
            if sw_speed >= self.config["sw_speed_extreme"]:
                speed_score = 1.0
            elif sw_speed >= self.config["sw_speed_storm"]:
                speed_score = 0.7
            elif sw_speed >= self.config["sw_speed_elevated"]:
                speed_score = 0.4
            else:
                speed_score = 0.0
            density_score = 0.0
            if sw_density is not None:
                self.metadata["sw_density_pcm3"] = sw_density
                if sw_density >= self.config["sw_density_storm"]:
                    density_score = 0.7
                elif sw_density >= self.config["sw_density_elevated"]:
                    density_score = 0.3
            self.channels["solar_wind"] = min(1.0, (speed_score + density_score) / 1.7)

        if bz is not None:
            self.metadata["imf_bz_nt"] = bz
            if bz <= self.config["bz_coupling_extreme"]:
                self.channels["imf_bz"] = 1.0
                self.metadata["bz_coupling"] = "EXTREME"
            elif bz <= self.config["bz_coupling_strong"]:
                self.channels["imf_bz"] = 0.8
                self.metadata["bz_coupling"] = "STRONG"
            elif bz <= self.config["bz_coupling_moderate"]:
                self.channels["imf_bz"] = 0.5
                self.metadata["bz_coupling"] = "MODERATE"
            elif bz <= self.config["bz_coupling_weak"]:
                self.channels["imf_bz"] = 0.25
                self.metadata["bz_coupling"] = "WEAK"
            else:
                self.channels["imf_bz"] = 0.0
                self.metadata["bz_coupling"] = "NONE"

        if proton is not None:
            self.metadata["proton_flux_pfu"] = proton
            if proton >= self.config["proton_s3"]:
                self.channels["proton_flux"] = 1.0
                self.metadata["proton_class"] = "S3_STRONG"
            elif proton >= self.config["proton_s2"]:
                self.channels["proton_flux"] = 0.6
                self.metadata["proton_class"] = "S2_MODERATE"
            elif proton >= self.config["proton_s1"]:
                self.channels["proton_flux"] = 0.3
                self.metadata["proton_class"] = "S1_MINOR"
            else:
                self.channels["proton_flux"] = 0.0
                self.metadata["proton_class"] = "NORMAL"

        w = self.config
        composite = (
            self.channels["kp_index"] * w["weight_kp"]
            + self.channels["solar_wind"] * w["weight_solar_wind"]
            + self.channels["imf_bz"] * w["weight_bz"]
            + self.channels["proton_flux"] * w["weight_proton"]
        )
        self.metadata["channel_scores"] = dict(self.channels)
        return round(min(1.0, composite), 4)

    def load_fixture(self, fixture_path: str) -> None:
        """Load historical Kp data for backtesting. Call before backtest."""
        from pathlib import Path

        path = Path(fixture_path)
        if not path.exists():
            self._historical_kp = {}
            return
        with open(path) as f:
            self._historical_kp = json.load(f)
        logger.info("Celestial: loaded %d days of Kp data", len(self._historical_kp))

    def _get_value(self, observation: dict | None, key: str, fetch_fn: object) -> float | None:
        if observation and key in observation and observation[key] is not None:
            return observation[key]
        if key == "kp_index" and hasattr(self, "_historical_kp") and observation and "date" in observation:
            date_str = str(observation["date"])[:10]
            if date_str in self._historical_kp:
                return self._historical_kp[date_str].get("kp_max")
        # Skip live fetches during backtest (avoids network spam and slowdown)
        if os.environ.get("GAIA_DISABLE_EVIDENCE") or (
            hasattr(self, "_historical_kp") and self._historical_kp
        ):
            return None
        try:
            return fetch_fn()
        except Exception as e:
            logger.warning("Celestial: failed to fetch %s: %s", key, e)
            return None

    def _cached_fetch(self, url: str, cache_key: str) -> object:
        now = datetime.now(timezone.utc)
        if cache_key in self._cache:
            expiry = self._cache_expiry.get(cache_key, now)
            if now < expiry:
                return self._cache[cache_key]
        data = self._do_fetch(url)
        if data is not None:
            self._cache[cache_key] = data
            self._cache_expiry[cache_key] = now + timedelta(seconds=self._cache_ttl_seconds)
        return data

    def _do_fetch(self, url: str) -> object:
        if self.fetcher:
            return self.fetcher(url)
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "GAIA-Weather-Engine"})
            with urllib.request.urlopen(req, timeout=self.config["fetch_timeout_seconds"]) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            logger.warning("Celestial fetch failed for %s: %s", url, e)
            return None

    def _fetch_kp(self) -> float | None:
        data = self._cached_fetch(SWPC_URLS["kp_index"], "kp")
        if not data or len(data) < 2:
            return None
        try:
            latest = data[-1]
            return float(latest[1])
        except (IndexError, ValueError, TypeError):
            return None

    def _fetch_sw_speed(self) -> float | None:
        data = self._cached_fetch(SWPC_URLS["solar_wind_plasma"], "plasma")
        if not data or len(data) < 2:
            return None
        try:
            for row in reversed(data[1:]):
                speed = row[1] if len(row) > 1 else None
                if speed is not None and speed != "":
                    return float(speed)
            return None
        except (IndexError, ValueError, TypeError):
            return None

    def _fetch_sw_density(self) -> float | None:
        data = self._cached_fetch(SWPC_URLS["solar_wind_plasma"], "plasma")
        if not data or len(data) < 2:
            return None
        try:
            for row in reversed(data[1:]):
                density = row[2] if len(row) > 2 else None
                if density is not None and density != "":
                    return float(density)
            return None
        except (IndexError, ValueError, TypeError):
            return None

    def _fetch_bz(self) -> float | None:
        data = self._cached_fetch(SWPC_URLS["solar_wind_mag"], "mag")
        if not data or len(data) < 2:
            return None
        try:
            for row in reversed(data[1:]):
                bz = row[3] if len(row) > 3 else None
                if bz is not None and bz != "":
                    return float(bz)
            return None
        except (IndexError, ValueError, TypeError):
            return None

    def _fetch_proton(self) -> float | None:
        data = self._cached_fetch(SWPC_URLS["proton_flux"], "proton")
        if not data:
            return None
        try:
            latest = data[-1] if isinstance(data, list) else None
            if latest and "flux" in latest:
                return float(latest["flux"])
            return None
        except (IndexError, ValueError, TypeError):
            return None

    def get_evidence(self) -> dict:
        return {
            "engine": "celestial",
            "channels": dict(self.channels),
            "metadata": dict(self.metadata),
            "swpc_urls": dict(SWPC_URLS),
        }

    def reset(self) -> None:
        self._cache.clear()
        self._cache_expiry.clear()
        self.channels = {}
        self.metadata = {}
