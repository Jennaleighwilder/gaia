"""
GAIA Moisture Engine
Scores atmospheric moisture loading and transport proxies.
"""

from __future__ import annotations

from runtime.engines.common import clamp, circular_spread_deg

MOISTURE_CHANNELS = {
    "precipitable_water": {"weight": 0.25},
    "gps_pw": {"weight": 0.0},
    "t_td_convergence": {"weight": 0.0},
    "dewpoint_magnitude": {"weight": 0.25},
    "dewpoint_trend": {"weight": 0.20},
    "relative_humidity": {"weight": 0.15},
    "moisture_convergence_proxy": {"weight": 0.15},
}


class MoistureEngine:
    def __init__(self):
        self.history = {}
        self.max_history = 72

    def ingest(self, station_id, timestamp, **data):
        self.history.setdefault(station_id, []).append({"timestamp": timestamp, **data})
        if len(self.history[station_id]) > self.max_history:
            self.history[station_id] = self.history[station_id][-self.max_history:]

    def score(self, station_id, **current_data):
        history = self.history.get(station_id, [])
        dewpoint_f = current_data.get("dewpoint_f")
        humidity_pct = current_data.get("humidity_pct")
        pw = current_data.get("precipitable_water_in")
        prior_dewpoint_f = current_data.get("prior_dewpoint_f")
        network_observations = current_data.get("network_observations", [])
        t_td_rate = current_data.get("t_td_convergence_rate_per_hr")
        channels = {name: 0.0 for name in MOISTURE_CHANNELS}

        # Prefer fixture gps_pw score (0–1, East TN climatology) when present
        gps_pw_score = current_data.get("gps_pw")
        if gps_pw_score is not None:
            channels["gps_pw"] = clamp(float(gps_pw_score))
        if pw is not None:
            channels["precipitable_water"] = clamp((pw - 0.7) / 1.3)
            if gps_pw_score is None:
                channels["gps_pw"] = channels["precipitable_water"]

        if t_td_rate is not None and t_td_rate > 0:
            channels["t_td_convergence"] = clamp(min(1.0, t_td_rate / 2.0))

        if dewpoint_f is not None:
            channels["dewpoint_magnitude"] = clamp((dewpoint_f - 45.0) / 25.0)

        if len(history) >= 9 and dewpoint_f is not None and history[-9].get("dewpoint_f") is not None:
            rise = dewpoint_f - history[-9]["dewpoint_f"]
            channels["dewpoint_trend"] = clamp(max(0.0, rise) / 8.0)
        elif dewpoint_f is not None and prior_dewpoint_f is not None:
            rise = dewpoint_f - prior_dewpoint_f
            channels["dewpoint_trend"] = clamp(max(0.0, rise) / 8.0)

        if humidity_pct is not None:
            channels["relative_humidity"] = clamp((humidity_pct - 50.0) / 45.0)

        dewpoints = [o.get("dewpoint_f") for o in network_observations if o.get("dewpoint_f") is not None]
        winds = [o.get("wind_direction_deg") for o in network_observations if o.get("wind_direction_deg") is not None]
        if dewpoint_f is not None:
            dewpoints.append(dewpoint_f)
        if current_data.get("wind_direction_deg") is not None:
            winds.append(current_data.get("wind_direction_deg"))
        if len(dewpoints) >= 2:
            avg_dp = sum(dewpoints) / len(dewpoints)
            direction_spread = circular_spread_deg([w for w in winds if w is not None]) if winds else 0.0
            moisture_pooling = clamp((avg_dp - 60.0) / 12.0)
            convergence_shape = clamp(direction_spread / 90.0)
            channels["moisture_convergence_proxy"] = round((moisture_pooling * 0.6) + (convergence_shape * 0.4), 4)

        weighted = sum(channels[name] * MOISTURE_CHANNELS[name]["weight"] for name in channels)
        return {
            "engine": "moisture",
            "score": round(clamp(weighted), 4),
            "channels": channels,
        }
