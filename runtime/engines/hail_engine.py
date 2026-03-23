"""
Hail Engine — VIL, echo top, GOES growth, instability.

Primary signal: VIL. Baseball hail (VIL>=60) = EMERGENCY.
"""

from __future__ import annotations

from runtime.engines.common import clamp


class HailEngine:
    def score(
        self,
        region: str,
        payload: dict | None = None,
        engine_scores: dict | None = None,
        **kwargs,
    ) -> dict:
        payload = payload or {}
        engine_scores = engine_scores or {}
        radar = payload.get("radar_fixture") or {}
        vil = float(radar.get("vil") or radar.get("VIL") or 0)
        echo_top = float(radar.get("echo_top_km") or 0)
        goes = payload.get("goes_data") or payload.get("goes") or {}
        cloud_top_growth = float(goes.get("cloud_top_growth_rate") or 0)
        inst_score = float(engine_scores.get("instability") or 0)

        if vil >= 60:
            vil_score = 1.0
        elif vil >= 40:
            vil_score = 0.8
        elif vil >= 20:
            vil_score = 0.5
        else:
            vil_score = 0.1

        if echo_top >= 15:
            top_score = 1.0
        elif echo_top >= 12:
            top_score = 0.7
        elif echo_top >= 9:
            top_score = 0.4
        else:
            top_score = 0.1

        if cloud_top_growth > 5:
            growth_score = 1.0
        elif cloud_top_growth > 3:
            growth_score = 0.6
        else:
            growth_score = 0.2

        hail_score = (
            vil_score * 0.4
            + top_score * 0.3
            + growth_score * 0.2
            + inst_score * 0.1
        )
        hail_score = clamp(min(hail_score, 1.0))

        hail_size_estimate = "none"
        if vil >= 60:
            hail_size_estimate = "baseball"
        elif vil >= 40:
            hail_size_estimate = "golf_ball"
        elif vil >= 20:
            hail_size_estimate = "penny"

        return {
            "score": round(hail_score, 4),
            "hail_indicated": hail_score > 0.6,
            "hail_size_estimate": hail_size_estimate,
            "vil": round(vil, 2),
            "echo_top_km": round(echo_top, 2),
            "vil_score": round(vil_score, 2),
            "top_score": round(top_score, 2),
        }
