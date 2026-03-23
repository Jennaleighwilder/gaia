"""
Fire Engine — NASA FIRMS + NOAA Red Flag from ASOS.

Fire within 10 mi = WILDFIRE_WARNING. Fire within 5 mi of TRI = HAZMAT_FIRE_ALERT.
RH < 25% AND wind > 15mph AND soil < 0.20 = FIRE_WEATHER_WARNING.
"""

from __future__ import annotations

import math
from typing import Any


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3959
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class FireEngine:
    COUNTY_CENTROIDS = {
        "knox": (35.96, -83.99), "sevier": (35.78, -83.52), "blount": (35.69, -83.93),
        "greene": (36.17, -82.83), "hamblen": (36.22, -83.27), "hawkins": (36.44, -82.95),
        "washington": (36.30, -82.50), "grainger": (36.28, -83.51), "sullivan": (36.51, -82.30),
        "anderson": (36.11, -84.20),
    }

    def score(self, region: str, payload: dict | None = None, **kwargs) -> dict:
        payload = payload or {}
        fires = payload.get("firms") or {}
        if isinstance(fires, dict):
            fires = fires.get("fires", [])
        obs = payload.get("station_observations") or []
        obs = obs[0] if obs else {}
        soil = float(payload.get("soil_moisture", 0.5) or 0.5)
        tri_facilities = payload.get("tri_facilities") or []

        active_fire_score = 0.0
        red_flag_score = 0.0
        alerts = []

        clat, clon = self.COUNTY_CENTROIDS.get(region.lower(), (36.0, -83.5))

        for f in fires:
            dist = haversine_miles(f["lat"], f["lon"], clat, clon)
            frp = f.get("frp", 0) or 0
            if dist < 10:
                active_fire_score = max(active_fire_score, 0.9 - dist / 15)
                alerts.append("WILDFIRE_WARNING")
            for tri in tri_facilities:
                tlat = tri.get("lat") or clat
                tlon = tri.get("lon") or clon
                tdist = haversine_miles(f["lat"], f["lon"], tlat, tlon)
                if tdist < 5:
                    active_fire_score = 1.0
                    alerts.append("HAZMAT_FIRE_ALERT")

        rh = obs.get("humidity_pct") or obs.get("relhum_pct")
        wind = obs.get("wind_speed_mph") or 0
        if rh is not None and rh < 25 and wind > 15 and soil < 0.20:
            red_flag_score = 0.95
            alerts.append("FIRE_WEATHER_WARNING")

        score = max(active_fire_score, red_flag_score)
        return {
            "score": min(score, 1.0),
            "active_fire_score": active_fire_score,
            "red_flag_score": red_flag_score,
            "alerts": list(set(alerts)),
        }
