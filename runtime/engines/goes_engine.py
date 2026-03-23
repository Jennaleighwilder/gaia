"""
GOES-16 Nature Scale Engine — Tier 1

Measures atmosphere from space. No human sensor grid bias.
Full disk coverage every 5 minutes.
Source: NOAA GOES-16 on AWS S3 (public).
"""

from __future__ import annotations

from runtime.engines.common import clamp


class GoesEngine:
    """Tier 1: TPW from GOES-16 ABI-L2-TPWF. Nature-scale moisture."""

    def __init__(self):
        self.history = {}
        self.max_history = 24  # 5-min scans, ~2 hours

    def ingest(self, region: str, timestamp: str, **data) -> None:
        self.history.setdefault(region, []).append({"timestamp": timestamp, **data})
        if len(self.history[region]) > self.max_history:
            self.history[region] = self.history[region][-self.max_history :]

    def score(self, region: str, **current_data) -> dict:
        from runtime.data.goes_tpw import get_goes_tpw_mm, get_goes_tpw_score

        mm = get_goes_tpw_mm()
        score_val = get_goes_tpw_score()
        if score_val is None:
            return {
                "score": 0.0,
                "tpw_mm": None,
                "tpw_in": None,
                "source": "goes16",
                "available": False,
                "atmospheric_river_detected": False,
            }
        mm_val = round(mm, 2) if mm is not None else None
        atmospheric_river_detected = mm_val is not None and mm_val > 50
        return {
            "score": clamp(score_val),
            "tpw_mm": mm_val,
            "tpw_in": round(mm / 25.4, 4) if mm is not None else None,
            "source": "goes16",
            "available": True,
            "atmospheric_river_detected": atmospheric_river_detected,
            "atmospheric_river_orientation": "SW-NE" if atmospheric_river_detected else None,
        }
