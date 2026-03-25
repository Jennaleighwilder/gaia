"""
NEXRAD Radar Engine — Tier 1

Rotation in velocity data = tornado forming.
Source: Unidata NEXRAD Level II mirror on S3 (unidata-nexrad-level2, public HTTP).
"""

from __future__ import annotations

from runtime.engines.common import clamp
from runtime.data.nexrad_fetch import (
    ASOS_TO_NEXRAD,
    detect_velocity_couplet,
    fetch_latest_for_station,
    fetch_latest_kmrx,
)


class RadarEngine:
    """Tier 1: NEXRAD composite, velocity couplet, VIL. Tornado detection."""

    def __init__(self):
        self.history = {}
        self.max_history = 12  # ~1 hour at 5-min scans

    def ingest(self, region: str, timestamp: str, **data) -> None:
        self.history.setdefault(region, []).append({"timestamp": timestamp, **data})
        if len(self.history[region]) > self.max_history:
            self.history[region] = self.history[region][-self.max_history :]

    def score(self, region: str, payload: dict | None = None, **kwargs) -> dict:
        # Historical backtest: use pre-fetched fixture when present
        payload = payload or {}
        data = payload.get("radar_fixture")
        if not data:
            asos = payload.get("station")
            if asos and asos in ASOS_TO_NEXRAD:
                data = fetch_latest_for_station(ASOS_TO_NEXRAD[asos])
            if not data:
                data = fetch_latest_kmrx()
        if not data:
            return {
                "score": 0.0,
                "max_dbz": None,
                "rotation_score": 0.0,
                "vil": None,
                "tornado_indicated": False,
                "severe_indicated": False,
                "available": False,
            }

        # REFLECTIVITY SCORE
        max_dbz = data.get("composite_reflectivity")
        if max_dbz is None:
            refl_score = 0.1
        elif max_dbz >= 65:
            refl_score = 1.0
        elif max_dbz >= 55:
            refl_score = 0.8
        elif max_dbz >= 45:
            refl_score = 0.6
        elif max_dbz >= 35:
            refl_score = 0.4
        else:
            refl_score = 0.1

        # ROTATION SCORE
        rotation_score = detect_velocity_couplet(data)

        # VIL SCORE
        vil = data.get("vil") or 0
        if vil >= 60:
            vil_score = 1.0
        elif vil >= 40:
            vil_score = 0.7
        elif vil >= 20:
            vil_score = 0.4
        else:
            vil_score = 0.1

        # COMPOSITE
        radar_score = max(
            refl_score * 0.4 + rotation_score * 0.5 + vil_score * 0.1,
            rotation_score,
        )
        radar_score = clamp(radar_score)

        return {
            "score": radar_score,
            "max_dbz": max_dbz,
            "rotation_score": rotation_score,
            "vil": vil if vil else None,
            "tornado_indicated": rotation_score > 0.7,
            "severe_indicated": refl_score > 0.6,
            "available": True,
        }
