"""
GAIA Shear Engine
Scores wind organization using surface observations and cross-station proxies.
"""

from __future__ import annotations

from runtime.engines.common import clamp, circular_diff_deg, circular_spread_deg, signed_circular_delta_deg

SHEAR_CHANNELS = {
    "surface_wind_speed": {"weight": 0.15},
    "gust_factor": {"weight": 0.15},
    "wind_direction_change": {"weight": 0.20},
    "cross_station_convergence": {"weight": 0.20},
    "speed_variability": {"weight": 0.10},
    "directional_spread": {"weight": 0.20},
    "wind_backing_rate": {"weight": 0.0},
    "sounding_bulk_shear": {"weight": 0.30},
    "sounding_srh": {"weight": 0.25},
}


class ShearEngine:
    def __init__(self):
        self.history = {}
        self.max_history = 72

    def ingest(self, station_id, timestamp, **data):
        self.history.setdefault(station_id, []).append({"timestamp": timestamp, **data})
        if len(self.history[station_id]) > self.max_history:
            self.history[station_id] = self.history[station_id][-self.max_history:]

    def score(self, station_id, **current_data):
        history = self.history.get(station_id, [])
        wind_speed_mph = current_data.get("wind_speed_mph")
        wind_gust_mph = current_data.get("wind_gust_mph")
        wind_direction_deg = current_data.get("wind_direction_deg")
        prior_wind_direction_deg = current_data.get("prior_wind_direction_deg")
        network_observations = current_data.get("network_observations", [])
        upper_air = current_data.get("upper_air") or {}
        channels = {name: 0.0 for name in SHEAR_CHANNELS}

        if wind_speed_mph is not None:
            channels["surface_wind_speed"] = clamp((wind_speed_mph - 10.0) / 25.0)

        if wind_speed_mph and wind_gust_mph:
            gust_factor = wind_gust_mph / max(wind_speed_mph, 1.0)
            channels["gust_factor"] = clamp((gust_factor - 1.2) / 1.0)

        if len(history) >= 3 and wind_direction_deg is not None and history[-3].get("wind_direction_deg") is not None:
            delta = circular_diff_deg(wind_direction_deg, history[-3]["wind_direction_deg"])
            channels["wind_direction_change"] = clamp(delta / 90.0)
            signed_delta = signed_circular_delta_deg(wind_direction_deg, history[-3]["wind_direction_deg"])
            if signed_delta < 0:
                channels["wind_backing_rate"] = clamp(abs(signed_delta) / 90.0)
        elif wind_direction_deg is not None and prior_wind_direction_deg is not None:
            delta = circular_diff_deg(wind_direction_deg, prior_wind_direction_deg)
            channels["wind_direction_change"] = clamp(delta / 90.0)
            signed_delta = signed_circular_delta_deg(wind_direction_deg, prior_wind_direction_deg)
            if signed_delta < 0:
                channels["wind_backing_rate"] = clamp(abs(signed_delta) / 90.0)

        speeds = [o.get("wind_speed_mph") for o in network_observations if o.get("wind_speed_mph") is not None]
        if wind_speed_mph is not None:
            speeds.append(wind_speed_mph)
        if len(history) >= 4:
            recent = [h.get("wind_speed_mph") for h in history[-4:] if h.get("wind_speed_mph") is not None]
            if wind_speed_mph is not None:
                recent.append(wind_speed_mph)
            if len(recent) >= 3:
                variability = max(recent) - min(recent)
                channels["speed_variability"] = clamp(variability / 20.0)

        dirs = [o.get("wind_direction_deg") for o in network_observations if o.get("wind_direction_deg") is not None]
        if wind_direction_deg is not None:
            dirs.append(wind_direction_deg)
        if len(dirs) >= 2:
            spread = circular_spread_deg(dirs)
            channels["directional_spread"] = clamp(spread / 120.0)
            max_pair = 0.0
            for i, first in enumerate(dirs):
                for second in dirs[i + 1:]:
                    max_pair = max(max_pair, circular_diff_deg(first, second))
            if max_pair >= 120.0 and max(speeds or [0.0]) >= 10.0:
                channels["cross_station_convergence"] = clamp(max_pair / 180.0)

        bulk_shear_6km = upper_air.get("bulk_shear_0_6km_kts")
        if bulk_shear_6km is not None:
            if bulk_shear_6km < 20:
                channels["sounding_bulk_shear"] = 0.05
            elif bulk_shear_6km < 35:
                channels["sounding_bulk_shear"] = 0.4
            elif bulk_shear_6km < 50:
                channels["sounding_bulk_shear"] = 0.7
            else:
                channels["sounding_bulk_shear"] = 0.95

        srh_1km = upper_air.get("srh_0_1km_m2s2")
        if srh_1km is not None:
            if srh_1km < 50:
                channels["sounding_srh"] = 0.05
            elif srh_1km < 150:
                channels["sounding_srh"] = 0.4
            elif srh_1km < 300:
                channels["sounding_srh"] = 0.7
            else:
                channels["sounding_srh"] = 0.95

        weighted = sum(channels[name] * SHEAR_CHANNELS[name]["weight"] for name in channels)
        if channels["sounding_bulk_shear"] > 0:
            weighted += channels["sounding_bulk_shear"] * 0.18
        if channels["sounding_srh"] > 0:
            weighted += channels["sounding_srh"] * 0.12
        severe_count = sum(1 for value in channels.values() if value >= 0.5)
        if severe_count >= 3:
            weighted += min(0.25, severe_count * 0.07)
        if (
            (wind_speed_mph or 0.0) >= 20.0
            and (wind_gust_mph or 0.0) >= 30.0
            and channels["wind_direction_change"] >= 0.3
        ):
            weighted += 0.18
        if (
            (wind_speed_mph or 0.0) >= 20.0
            and (wind_gust_mph or 0.0) >= 30.0
            and 0.05 <= channels["directional_spread"] <= 0.35
        ):
            weighted += 0.12
        if (
            (wind_speed_mph or 0.0) >= 20.0
            and (wind_gust_mph or 0.0) >= 30.0
            and channels["wind_direction_change"] >= 0.3
            and channels["directional_spread"] < 0.05
        ):
            weighted += 0.14

        # Nocturnal low-level jet (LLJ) — TN/southeast overnight wind surge
        llj_score = 0.0
        ts = current_data.get("timestamp") or ""
        if ts and len(history) >= 3:
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                local_hr = (dt.hour - 5) % 24  # East TN ~UTC-5
                recent = [h.get("wind_speed_mph") for h in history[-6:] if h.get("wind_speed_mph") is not None]
                if wind_speed_mph is not None:
                    recent.append(wind_speed_mph)
                wind_increasing = len(recent) >= 3 and recent[-1] > (recent[0] or 0) + 2
                backing = channels.get("wind_backing_rate", 0) >= 0.2
                if 0 <= local_hr <= 6 and wind_increasing and backing:
                    llj_score = 0.6
                    channels["low_level_jet"] = llj_score
            except Exception:
                pass
        if llj_score > 0:
            weighted += llj_score

        return {
            "engine": "shear",
            "score": round(clamp(weighted), 4),
            "channels": channels,
        }
