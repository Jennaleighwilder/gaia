"""
GAIA Hydrological Engine — streamflow, flash flood risk.
CONTEXT_ONLY initially. Sources: USGS Water Services (real-time streamflow).
"""

from __future__ import annotations

from runtime.engines.common import clamp
from runtime.data.usgs_streamflow import (
    EAST_TN_GAUGE_IDS,
    fetch_realtime,
    load_flood_stages,
)


class HydrologicalEngine:
    """Scores flash flood risk from USGS stream gauges. CONTEXT_ONLY."""

    def __init__(self):
        self._cache = {}
        self._cache_ts = 0
        self._stale_sec = 900  # 15 min

    def _get_gauge_data(self):
        import time
        now = time.time()
        if now - self._cache_ts < self._stale_sec and self._cache:
            return self._cache
        self._cache = fetch_realtime()
        self._cache_ts = now
        return self._cache

    def score(self, station_id="region", **current_data):
        flood_stages = load_flood_stages()
        gauges = self._get_gauge_data()

        stage_ratios = []
        rising_flags = []
        above_flood = 0

        for site_no, g in gauges.items():
            stage = g.get("gage_height_ft")
            if stage is None:
                continue
            flood_ft = flood_stages.get(site_no)
            if flood_ft and flood_ft > 0:
                ratio = stage / flood_ft
                stage_ratios.append(clamp(ratio, 0.0, 2.0))
                if ratio >= 1.0:
                    above_flood += 1

        stream_stage_ratio = round(sum(stage_ratios) / len(stage_ratios), 4) if stage_ratios else 0.0
        gauges_above_flood = above_flood

        channels = {
            "stream_stage_vs_flood_ratio": round(stream_stage_ratio, 4),
            "gauges_above_flood_stage": gauges_above_flood,
            "gauges_reporting": len([g for g in gauges.values() if g.get("gage_height_ft") is not None]),
        }

        weighted = clamp(stream_stage_ratio * 0.7 + (0.3 if gauges_above_flood else 0))
        return {
            "engine": "hydrological",
            "score": round(clamp(weighted), 4),
            "channels": channels,
        }
