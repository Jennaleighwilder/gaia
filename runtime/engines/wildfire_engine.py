"""
Wildfire Engine — dedicated detection path for fire (not convective).

Three precursor signals:
1. RED FLAG CONDITIONS: RH < 15%, wind > 15mph, soil < 0.20, temp > 90F (pre-fire lead time)
2. FIRMS SATELLITE: NASA heat anomalies, FRP-based scoring, distance weighting
3. SMOKE/VISIBILITY: ASOS present_weather FU/HZ, visibility < 3mi with no precip

Governor wiring:
- red_flag + firms_nearby -> WILDFIRE_WARNING
- red_flag only -> FIRE_WEATHER_WARNING
- firms_nearby only -> WILDFIRE_WATCH
- fire within 5mi of TRI -> HAZMAT_FIRE_ALERT
"""

from __future__ import annotations

import math
from typing import Any


def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(min(1, a)))


class WildfireEngine:
    """Dedicated wildfire detection — red flag, FIRMS, smoke."""

    def score(self, region: str, payload: dict | None = None, **kwargs) -> dict:
        payload = payload or {}
        fixture = payload.get("wildfire_fixture") or {}
        obs_list = payload.get("station_observations") or []
        obs = obs_list[0] if obs_list else {}

        # --- SIGNAL 1: Red flag conditions ---
        rh = obs.get("humidity_pct") or obs.get("relhum_pct") or fixture.get("relative_humidity_pct")
        if rh is None and obs.get("temperature_f") is not None and obs.get("dewpoint_f") is not None:
            t_f, d_f = obs["temperature_f"], obs["dewpoint_f"]
            t_c = (t_f - 32) * 5 / 9
            d_c = (d_f - 32) * 5 / 9
            rh = 100 * math.exp((17.27 * d_c) / (237.3 + d_c) - (17.27 * t_c) / (237.3 + t_c))
        wind = obs.get("wind_speed_mph") or fixture.get("wind_speed_mph") or 0
        temp = obs.get("temperature_f") or fixture.get("temperature_f")
        soil = float(payload.get("soil_moisture") or fixture.get("soil_moisture") or 0.5)

        red_flag_conditions = 0
        if rh is not None and rh < 15:
            red_flag_conditions += 1
        if wind > 15:
            red_flag_conditions += 1
        if soil < 0.20:
            red_flag_conditions += 1
        if temp is not None and temp > 90:
            red_flag_conditions += 1

        red_flag_score = 0.0
        if red_flag_conditions >= 4:
            red_flag_score = 0.95
        elif red_flag_conditions >= 3:
            red_flag_score = 0.7

        # --- SIGNAL 2: FIRMS satellite ---
        fires = fixture.get("firms_fires") or payload.get("firms") or []
        if isinstance(fires, dict):
            fires = fires.get("fires", [])
        county_lat = fixture.get("county_lat") or 36.5
        county_lon = fixture.get("county_lon") or -119.5
        tri_facilities = payload.get("tri_facilities") or []

        fire_score = 0.0
        firms_nearby = False
        hazmat_fire = False
        for f in fires:
            flat = f.get("lat") or f.get("latitude")
            flon = f.get("lon") or f.get("longitude")
            if flat is None or flon is None:
                continue
            dist = haversine_mi(flat, flon, county_lat, county_lon)
            if dist > 50:
                continue
            firms_nearby = True
            frp = float(f.get("frp", 0) or f.get("fire_radiative_power", 0) or 0)
            if frp > 1000:
                base = 1.0
            elif frp > 100:
                base = 0.7
            elif frp > 10:
                base = 0.4
            else:
                base = 0.2
            mult = 1.0 if dist < 5 else (0.7 if dist < 20 else 0.4)
            fire_score = max(fire_score, base * mult)
            for tri in tri_facilities:
                tlat = tri.get("lat") or tri.get("latitude")
                tlon = tri.get("lon") or tri.get("longitude")
                if tlat is not None and tlon is not None:
                    tdist = haversine_mi(flat, flon, tlat, tlon)
                    if tdist < 5:
                        hazmat_fire = True
                        fire_score = 1.0

        # --- SIGNAL 3: Smoke/visibility ---
        present = (obs.get("present_weather") or obs.get("metar") or "").upper()
        vis = obs.get("visibility_mi")
        precip = obs.get("precip_1h_in") or 0
        smoke_score = 0.0
        if "FU" in present:
            smoke_score = 0.8
        elif "HZ" in present:
            smoke_score = 0.4
        elif vis is not None and vis < 3 and (precip or 0) < 0.01:
            smoke_score = 0.5

        # --- Combine ---
        alerts = []
        if hazmat_fire:
            alerts.append("HAZMAT_FIRE_ALERT")
        if red_flag_conditions >= 4 and firms_nearby:
            alerts.append("WILDFIRE_WARNING")
        elif red_flag_conditions >= 3 and firms_nearby:
            alerts.append("WILDFIRE_WARNING")
        elif red_flag_conditions >= 4:
            alerts.append("FIRE_WEATHER_WARNING")
        elif red_flag_conditions >= 3:
            alerts.append("FIRE_WEATHER_WATCH")
        elif firms_nearby:
            alerts.append("WILDFIRE_WATCH")
        if smoke_score > 0.5:
            alerts.append("SMOKE_DETECTED")

        wildfire_certain = (
            fire_score >= 0.7 or (red_flag_score >= 0.7 and firms_nearby) or hazmat_fire
            or red_flag_score >= 0.9  # Extreme red flag = FIRE_WEATHER_WARNING
        )
        score = max(red_flag_score, fire_score, smoke_score, 0.0)
        score = min(score, 1.0)

        return {
            "score": round(score, 4),
            "red_flag_score": red_flag_score,
            "red_flag_conditions": red_flag_conditions,
            "firms_fire_score": fire_score,
            "firms_nearby": firms_nearby,
            "smoke_score": smoke_score,
            "wildfire_certain": wildfire_certain,
            "alerts": list(set(alerts)),
        }
