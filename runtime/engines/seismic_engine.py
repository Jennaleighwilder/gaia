"""
Seismic Engine — USGS earthquakes + East TN scoring.

M4+ near Holston AAP = HAZMAT_SEISMIC_ALERT (immediate escalation).
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

HOLSTON_AAP = (36.44, -82.95)
EAST_TN_CENTROID = (36.0, -83.5)
DAM_APPROX = [(36.1, -83.4), (35.9, -83.8)]


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3959
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class SeismicEngine:
    def __init__(self):
        self.history: list[dict] = []

    def score(self, region: str, payload: dict | None = None, **kwargs) -> dict:
        payload = payload or {}
        quakes = payload.get("earthquakes") or payload.get("usgs_earthquakes")
        if isinstance(quakes, dict):
            quakes = quakes.get("features", []) if "features" in quakes else []
        if not quakes:
            return {"score": 0.0, "alerts": [], "hazmat_seismic": False}

        county_lat, county_lon = self._county_coords(region)
        max_score = 0.0
        alerts: list[str] = []
        hazmat_seismic = False

        for f in quakes[:50]:
            props = f.get("properties", {})
            geom = f.get("geometry", {})
            coords = geom.get("coordinates", [0, 0, 0])
            mag = float(props.get("mag", 0) or 0)
            qlon, qlat = coords[0], coords[1]
            dist_county = haversine_miles(qlat, qlon, county_lat, county_lon)
            dist_holston = haversine_miles(qlat, qlon, HOLSTON_AAP[0], HOLSTON_AAP[1])

            score = 0.0
            if dist_county < 50:
                if mag >= 4.0:
                    score = 1.0
                    alerts.append("SEISMIC_ALERT")
                elif mag >= 3.0:
                    score = 0.7
                    alerts.append("WARNING")
                elif mag >= 2.0:
                    score = 0.3
                    alerts.append("WATCH")
            if dist_county < 100 and mag >= 5.0:
                score = max(score, 0.8)
                alerts.append("WARNING")

            for dam in DAM_APPROX:
                if haversine_miles(qlat, qlon, dam[0], dam[1]) < 30:
                    alerts.append("DAM_FAILURE_WATCH")

            if dist_holston < 25 and mag >= 4.0:
                hazmat_seismic = True
                alerts.append("HAZMAT_SEISMIC_ALERT")
                score = 1.0

            max_score = max(max_score, score)

        swarm = self._check_swarm(quakes)
        if swarm:
            alerts.append("SWARM_WATCH")
            max_score = max(max_score, 0.5)

        return {
            "score": min(max_score, 1.0),
            "alerts": list(set(alerts)),
            "hazmat_seismic": hazmat_seismic,
            "earthquake_count": len(quakes),
        }

    def _county_coords(self, region: str) -> tuple[float, float]:
        from runtime.engines.terrain_engine import COUNTY_CENTROIDS
        return COUNTY_CENTROIDS.get(region.lower(), EAST_TN_CENTROID)

    def _check_swarm(self, quakes: list) -> bool:
        if len(quakes) < 3:
            return False
        lats = []
        lons = []
        for f in quakes[:24]:
            geom = f.get("geometry", {})
            coords = geom.get("coordinates", [0, 0, 0])
            lons.append(coords[0])
            lats.append(coords[1])
        if not lats:
            return False
        span_lat = max(lats) - min(lats)
        span_lon = max(lons) - min(lons)
        return span_lat < 0.5 and span_lon < 0.5
