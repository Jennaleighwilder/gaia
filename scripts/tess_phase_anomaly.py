"""
Phase-anomaly TESS: score departure from a trailing monthly baseline (within-phase
discrimination) instead of absolute MEI/AO/PDO floors.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from statistics import mean, pstdev
from typing import Any


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, x))))


@dataclass
class PhaseAnomalyScorer:
    """24-month (or shorter when unavailable) z-scores vs trailing mean, no NumPy."""

    phase_window: int = 24

    def compute_phase_anomaly(
        self, index_values: list[float], current_idx: int, phase_window: int | None = None
    ) -> float:
        pw = phase_window if phase_window is not None else self.phase_window
        if current_idx < 1 or not index_values:
            return 0.0
        ws = min(pw, current_idx)
        if ws < 12:
            return 0.0
        window = index_values[current_idx - ws : current_idx]
        if len(window) < 12:
            return 0.0
        m = mean(window)
        try:
            sd = pstdev(window)
        except Exception:
            return 0.0
        if sd < 0.01:
            return 0.0
        return (index_values[current_idx] - m) / sd

    def score_month(self, _date: datetime, index_history: dict[str, list[float]]) -> dict[str, Any]:
        """
        index_history: {'ao','mei','pdo','pna'} -> chronological values through scoring month.
        """
        anomalies: dict[str, float] = {}
        for idx_name, values in index_history.items():
            if not values or len(values) < 2:
                anomalies[idx_name] = 0.0
                continue
            ci = len(values) - 1
            anomalies[idx_name] = self.compute_phase_anomaly(values, ci)

        mei_z = anomalies.get("mei", 0.0)
        pdo_z = anomalies.get("pdo", 0.0)
        ao_z = anomalies.get("ao", 0.0)
        pna_z = anomalies.get("pna", 0.0)

        # Deeper La Niña / cold PDO vs recent baseline -> positive contribution
        origin_z = -0.55 * mei_z - 0.45 * pdo_z
        # Negative AO / positive PNA vs baseline -> favorable for CONUS trough/meridional flow
        transport_z = -0.55 * ao_z + 0.45 * pna_z

        origin_phase_score = round(_sigmoid(origin_z), 3)
        transport_phase_score = round(_sigmoid(transport_z), 3)

        combined = (
            anomalies.get("ao", 0) * 0.40
            + (-anomalies.get("mei", 0)) * 0.30
            + (-anomalies.get("pdo", 0)) * 0.20
            + anomalies.get("pna", 0) * 0.10
        )
        phase_anomaly_score = round(_sigmoid(combined), 3)

        return {
            "anomalies": anomalies,
            "origin_phase_score": origin_phase_score,
            "transport_phase_score": transport_phase_score,
            "combined_anomaly": round(combined, 4),
            "phase_anomaly_score": phase_anomaly_score,
        }
