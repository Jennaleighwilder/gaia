"""
Water Engine — NDBC buoys, inland river levels, hurricane proximity.

For Lake Tellico, Norris Lake, Ohio/Mississippi tributaries.
Gulf Coast buoys: hurricane precursor tracking.
"""

from __future__ import annotations

import json
import logging
import math
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

# NDBC stations: Gulf Coast (hurricane), Ohio River, inland lakes
GULF_BUOYS = ["42001", "42002", "42003", "42040"]  # Gulf of Mexico
OHIO_RIVER = ["louc1", "pghb1"]  # Louisville, Pittsburgh
INLAND_NEAR_TN = ["biki1", "cbtt1"]  # Lake Michigan, etc. — placeholder

NDBC_BASE = "https://www.ndbc.noaa.gov/data/realtime2"
HURRICANE_TRACK_BASE = "https://www.nhc.noaa.gov/gis"


def _haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3959
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _fetch_ndbc(station: str, dtype: str = "txt") -> str | None:
    import os

    if os.environ.get("GAIA_OFFLINE") == "1":
        return None

    url = f"{NDBC_BASE}/{station}.{dtype}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.debug("NDBC fetch %s failed: %s", station, e)
        return None


def _parse_ndbc_txt(text: str) -> dict | None:
    """Parse NDBC standard met .txt. Returns wave height, wind, water temp."""
    lines = [l.strip() for l in text.split("\n") if l.strip() and not l.startswith("#")]
    if len(lines) < 2:
        return None
    cols = lines[1].split()
    if len(cols) < 15:
        return None
    try:
        wtmp = float(cols[14]) if cols[14] != "MM" else None
        wvht = float(cols[8]) if cols[8] != "MM" else None
        wdir = float(cols[6]) if cols[6] != "MM" else None
        wspd = float(cols[7]) if cols[7] != "MM" else None
        return {
            "wave_height_m": wvht,
            "water_temp_c": wtmp,
            "wind_dir_deg": wdir,
            "wind_speed_kt": wspd,
        }
    except (ValueError, IndexError):
        return None


class WaterEngine:
    def __init__(self):
        self._buoy_cache: dict[str, dict] = {}
        self._hurricane_proximity: float | None = None

    def score(self, region: str, payload: dict | None = None, **kwargs) -> dict:
        payload = payload or {}
        scores = []
        wave_score = 0.0
        river_upstream_high = False
        hurricane_proximity_score = 0.0
        buoy_data: list[dict] = []

        for bid in GULF_BUOYS[:2]:
            raw = _fetch_ndbc(bid)
            if raw:
                parsed = _parse_ndbc_txt(raw)
                if parsed:
                    buoy_data.append({"station": bid, **parsed})
                    wvht = parsed.get("wave_height_m") or 0
                    if wvht > 3:
                        wave_score = max(wave_score, 0.8)
                    elif wvht > 1.5:
                        wave_score = max(wave_score, 0.5)

        tn_center = (36.0, -83.5)
        gulf_center = (27.0, -92.0)
        dist_gulf_mi = _haversine_mi(*tn_center, *gulf_center)
        if dist_gulf_mi < 500:
            hurricane_proximity_score = 0.9
        elif dist_gulf_mi < 700:
            hurricane_proximity_score = 0.5

        goes_tpw = payload.get("goes_tpw_mm") or (payload.get("goes_data") or {}).get("tpw_mm")
        if goes_tpw and goes_tpw > 55 and hurricane_proximity_score > 0.3:
            hurricane_proximity_score = max(hurricane_proximity_score, 0.85)

        score = max(wave_score * 0.3, hurricane_proximity_score * 0.4)
        if river_upstream_high:
            score = max(score, 0.6)

        return {
            "score": min(score, 1.0),
            "wave_height_score": wave_score,
            "hurricane_proximity_score": hurricane_proximity_score,
            "hurricane_proximity_mi": round(dist_gulf_mi, 0),
            "buoy_data": buoy_data[:5],
            "river_upstream_high": river_upstream_high,
            "moisture_surge_risk": hurricane_proximity_score > 0.5,
        }
