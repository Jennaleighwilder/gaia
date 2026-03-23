"""
GAIA Regime Change Detection Engine.

Tracks daily atmospheric summaries and scores regime transitions.
"""

from __future__ import annotations

import math

from runtime.engines.common import clamp


class RegimeEngine:
    def __init__(self):
        self.daily_summaries = []
        self.max_days = 30

    def add_daily_summary(self, summary: dict) -> None:
        self.daily_summaries.append(summary)
        if len(self.daily_summaries) > self.max_days:
            self.daily_summaries = self.daily_summaries[-self.max_days:]

    def compute_regime_stability(self, summaries: list[dict] | None = None) -> dict:
        sample = summaries if summaries is not None else self.daily_summaries
        if len(sample) < 7:
            return {"stability": 0.5, "trend": "insufficient_data"}

        recent_7 = sample[-7:]
        pressures = [item.get("mean_pressure", 1013.0) for item in recent_7 if item.get("mean_pressure") is not None]
        if len(pressures) >= 5:
            pressure_mean = sum(pressures) / len(pressures)
            p_std = (sum((value - pressure_mean) ** 2 for value in pressures) / len(pressures)) ** 0.5
        else:
            p_std = 5.0

        wind_dirs = [item.get("dominant_wind_dir") for item in recent_7 if item.get("dominant_wind_dir") is not None]
        if len(wind_dirs) >= 5:
            sin_sum = sum(math.sin(math.radians(direction)) for direction in wind_dirs)
            cos_sum = sum(math.cos(math.radians(direction)) for direction in wind_dirs)
            wind_consistency = math.sqrt(sin_sum ** 2 + cos_sum ** 2) / len(wind_dirs)
        else:
            wind_consistency = 0.5

        temps = [item.get("mean_temp") for item in recent_7 if item.get("mean_temp") is not None]
        if len(temps) >= 5:
            diffs = [temps[idx + 1] - temps[idx] for idx in range(len(temps) - 1)]
            same_sign = sum(1 for idx in range(len(diffs) - 1) if diffs[idx] * diffs[idx + 1] > 0)
            temp_consistency = same_sign / max(len(diffs) - 1, 1)
        else:
            temp_consistency = 0.5

        pressure_stability = clamp(1.0 - (p_std / 10.0))
        overall = pressure_stability * 0.4 + wind_consistency * 0.35 + temp_consistency * 0.25
        return {
            "stability": round(clamp(overall), 4),
            "pressure_std_7d": round(p_std, 2),
            "wind_consistency_7d": round(wind_consistency, 4),
            "temp_consistency_7d": round(temp_consistency, 4),
        }

    def detect_transition(self) -> dict:
        if len(self.daily_summaries) < 10:
            return {"engine": "regime", "score": 0.0, "note": "insufficient history for regime detection"}

        prior_7 = self.daily_summaries[-10:-3]
        current_7 = self.daily_summaries[-7:]
        prior_stability = self.compute_regime_stability(prior_7)
        current_stability = self.compute_regime_stability(current_7)

        prior_score = prior_stability["stability"]
        current_score = current_stability["stability"]
        drop = prior_score - current_score

        if drop <= 0.0:
            score = 0.0
            state = "stable_or_improving"
        elif drop < 0.15:
            score = 0.15
            state = "minor_fluctuation"
        elif drop < 0.3:
            score = 0.45
            state = "regime_weakening"
        elif drop < 0.5:
            score = 0.7
            state = "regime_breaking"
        else:
            score = 0.9
            state = "major_regime_transition"

        return {
            "engine": "regime",
            "score": round(score, 4),
            "state": state,
            "prior_stability": round(prior_score, 4),
            "current_stability": round(current_score, 4),
            "stability_drop": round(drop, 4),
            "detail": current_stability,
        }
