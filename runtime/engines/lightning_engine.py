"""
GOES-16 GLM Lightning Engine — Tier 1

Replaces harmonic proxy with actual lightning data.
Flash rate > 10/min = active convection, > 50/min = intense.
"""

from __future__ import annotations

from runtime.engines.common import clamp


class LightningEngine:
    """Tier 1: GLM flash rate and energy. Active convection detection."""

    def __init__(self):
        self.history = {}
        self.max_history = 12  # 5-min windows

    def ingest(self, region: str, timestamp: str, **data) -> None:
        self.history.setdefault(region, []).append({"timestamp": timestamp, **data})
        if len(self.history[region]) > self.max_history:
            self.history[region] = self.history[region][-self.max_history :]

    def score(self, region: str, payload: dict | None = None, **kwargs) -> dict:
        payload = payload or {}
        data = payload.get("lightning_fixture")
        if data is None:
            try:
                from runtime.data.glm_lightning import fetch_glm_flash_stats
                data = fetch_glm_flash_stats()
            except Exception:
                data = {"flash_rate_per_min": 0.0, "energy_j": 0.0, "available": False}
        rate = data.get("flash_rate_per_min") or 0.0
        energy = data.get("energy_j") or 0.0
        available = data.get("available", True)
        if not available and rate == 0:
            return {
                "score": 0.0,
                "flash_rate_per_min": None,
                "energy_j": None,
                "active_convection": False,
                "intense_convection": False,
                "available": False,
            }
        # Score: 0-1 from flash rate
        if rate >= 50:
            score_val = 1.0
        elif rate >= 10:
            score_val = 0.5 + 0.5 * (rate - 10) / 40
        elif rate >= 2:
            score_val = 0.2 * (rate / 10)
        else:
            score_val = 0.05
        score_val = clamp(score_val)
        return {
            "score": score_val,
            "flash_rate_per_min": round(rate, 2),
            "energy_j": round(energy, 2),
            "active_convection": rate >= 10,
            "intense_convection": rate >= 50,
            "available": True,
        }
