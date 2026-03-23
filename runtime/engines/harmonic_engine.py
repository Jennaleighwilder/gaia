"""
GAIA Engine 16: HARMONIC — Schumann Resonance Proxy Engine

Uses multi-station thunder count as lightning proxy. Celestial feeds in as cavity modifier.
Context-only: provides leading indicators, doesn't vote in convergence until calibrated.
"""

from __future__ import annotations

import logging
from collections import deque

logger = logging.getLogger(__name__)

SR_MODES = [7.83, 14.3, 20.8, 27.3, 33.8, 39.0, 45.0, 50.0]


class HarmonicEngine:
    """
    Schumann Resonance Proxy via multi-station thunder count.
    Context-only: scores alongside backtest for separation analysis.
    """

    DEFAULTS = {
        "thunder_count_active": 2,
        "thunder_count_intense": 4,
        "thunder_count_extreme": 6,
        "weight_thunder": 0.5,
        "weight_celestial_modifier": 0.2,
        "history_max_hours": 48,
    }

    def __init__(self, config=None):
        self.config = {**self.DEFAULTS}
        if config:
            self.config.update(config)
        self.rate_history: deque = deque(maxlen=48)
        self.channels = {}
        self.metadata = {}

    def score(self, observation: dict) -> float:
        """
        Score regional convective/electromagnetic state.
        observation: thunder_count_nearby, celestial (optional modifier)
        """
        self.channels = {"lightning_proxy": 0.0, "celestial_modifier": 0.0}
        self.metadata = {}

        thunder = observation.get("thunder_count_nearby", 0)
        self.metadata["thunder_count_nearby"] = thunder
        self.rate_history.append(thunder)

        cfg = self.config
        if thunder >= cfg["thunder_count_extreme"]:
            self.channels["lightning_proxy"] = 1.0
        elif thunder >= cfg["thunder_count_intense"]:
            self.channels["lightning_proxy"] = 0.7
        elif thunder >= cfg["thunder_count_active"]:
            self.channels["lightning_proxy"] = 0.4
        elif thunder >= 1:
            self.channels["lightning_proxy"] = 0.15

        celestial = observation.get("celestial_score") or observation.get("celestial") or 0.0
        if isinstance(celestial, dict):
            celestial = celestial.get("score", 0.0)
        self.channels["celestial_modifier"] = min(0.5, float(celestial or 0) * 0.5)
        self.metadata["celestial_modifier"] = self.channels["celestial_modifier"]

        w = self.config
        composite = (
            self.channels["lightning_proxy"] * w["weight_thunder"]
            + self.channels["celestial_modifier"] * w["weight_celestial_modifier"]
        )
        return round(min(1.0, composite), 4)

    def get_evidence(self) -> dict:
        return {
            "engine": "harmonic",
            "channels": dict(self.channels),
            "metadata": dict(self.metadata),
            "schumann_modes_hz": SR_MODES,
        }

    def reset(self) -> None:
        self.rate_history.clear()
        self.channels = {}
        self.metadata = {}
