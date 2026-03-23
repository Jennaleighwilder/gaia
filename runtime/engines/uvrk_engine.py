"""
GAIA UVRK-1 Atmospheric Volatility Engine.

Applies the Universal Volatility Recursion Kernel to atmospheric
time-series volatility rather than financial markets.
"""

from __future__ import annotations

import math
from typing import List, Optional

from runtime.engines.common import clamp


def inverse_normal_cdf(p: float) -> float:
    if p <= 0.0:
        return -3.0
    if p >= 1.0:
        return 3.0
    if p == 0.5:
        return 0.0

    if p < 0.5:
        t = math.sqrt(-2.0 * math.log(p))
    else:
        t = math.sqrt(-2.0 * math.log(1.0 - p))

    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    result = t - (c0 + c1 * t + c2 * t * t) / (1 + d1 * t + d2 * t * t + d3 * t * t * t)
    return -result if p < 0.5 else result


def rolling_volatility(values: List[float], window: int = 12) -> List[float]:
    vols = []
    for idx in range(window, len(values) + 1):
        chunk = values[idx - window:idx]
        mean = sum(chunk) / len(chunk)
        variance = sum((value - mean) ** 2 for value in chunk) / len(chunk)
        vols.append(math.sqrt(variance))
    return vols


def percentile_rank(value: float, history: List[float]) -> float:
    if not history:
        return 0.5
    below = sum(1 for item in history if item < value)
    return below / len(history)


class UVRKAtmosphericEngine:
    THETA = 0.92
    KAPPA = 0.15
    SIGMA = 0.05

    VOL_WINDOW = 12
    RANK_WINDOW = 72

    VARIABLES = {
        "pressure_mb": {"weight": 0.30, "description": "Barometric pressure volatility"},
        "temperature_f": {"weight": 0.25, "description": "Temperature volatility"},
        "dewpoint_f": {"weight": 0.25, "description": "Dewpoint volatility"},
        "wind_speed_mph": {"weight": 0.20, "description": "Wind speed volatility"},
    }

    def __init__(self):
        self.history: dict[str, list[float]] = {}
        self.vol_history: dict[str, list[float]] = {}
        self.max_history = 500

    def ingest(self, observation: dict) -> None:
        for var_name in self.VARIABLES:
            value = observation.get(var_name)
            if value is None:
                continue
            self.history.setdefault(var_name, []).append(float(value))
            if len(self.history[var_name]) > self.max_history:
                self.history[var_name] = self.history[var_name][-self.max_history:]
            if len(self.history[var_name]) >= self.VOL_WINDOW:
                self.vol_history[var_name] = rolling_volatility(self.history[var_name], self.VOL_WINDOW)

    def predict_next_vol(self, var_name: str) -> Optional[float]:
        vols = self.vol_history.get(var_name, [])
        if len(vols) < 2:
            return None
        current_vol = vols[-1]
        recent_vols = vols[-min(len(vols), self.RANK_WINDOW):]
        rank = clamp(percentile_rank(current_vol, recent_vols), 0.01, 0.99)
        probit = inverse_normal_cdf(rank)
        predicted = self.THETA * current_vol + (1.0 - self.THETA) * self.KAPPA * probit
        return max(0.0, predicted)

    def score(self) -> dict:
        channel_scores = {}
        weighted_total = 0.0
        total_weight = 0.0

        for var_name, config in self.VARIABLES.items():
            predicted = self.predict_next_vol(var_name)
            vols = self.vol_history.get(var_name, [])
            if predicted is None or not vols:
                continue

            current_vol = vols[-1]
            recent_vols = vols[-min(len(vols), self.RANK_WINDOW):]
            mean_vol = (sum(recent_vols) / len(recent_vols)) if recent_vols else current_vol
            if mean_vol <= 0:
                channel_score = 0.0
            else:
                ratio = predicted / mean_vol
                channel_score = clamp((ratio - 0.5) / 2.5)

            channel_scores[var_name] = {
                "score": round(channel_score, 4),
                "current_vol": round(current_vol, 4),
                "predicted_vol": round(predicted, 4),
                "mean_vol": round(mean_vol, 4),
                "history_depth": len(vols),
            }
            weighted_total += channel_score * config["weight"]
            total_weight += config["weight"]

        overall = weighted_total / total_weight if total_weight else 0.0
        return {
            "engine": "uvrk",
            "score": round(clamp(overall), 4),
            "channels": channel_scores,
            "note": "UVRK-1 atmospheric volatility prediction",
        }
