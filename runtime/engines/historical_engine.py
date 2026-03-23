"""
GAIA Historical Analog Engine
Matches current conditions to known East Tennessee severe setups.
"""

from __future__ import annotations

from runtime.engines.common import clamp, month_key, parse_timestamp

KNOWN_SEVERE_SETUPS = [
    {
        "name": "Classic Southeast Tornado Setup",
        "conditions": {"dewpoint_f_min": 60, "wind_direction_range": (180, 240), "pressure_trend": "falling", "month_range": (3, 5)},
        "severity": 0.8,
    },
    {
        "name": "Gulf Moisture Flash Flood",
        "conditions": {"dewpoint_f_min": 65, "wind_direction_range": (150, 210), "pressure_mb_max": 1008, "month_range": (4, 9)},
        "severity": 0.7,
    },
    {
        "name": "Appalachian Lee Trough Severe",
        "conditions": {"wind_direction_range": (240, 300), "pressure_trend": "falling_fast", "month_range": (3, 6)},
        "severity": 0.6,
    },
    {
        "name": "Nocturnal Low-Level Jet Tornado",
        "conditions": {"dewpoint_f_min": 58, "wind_speed_mph_min": 15, "hour_range": (0, 8), "month_range": (3, 5)},
        "severity": 0.9,
    },
    {
        "name": "Summer Pulse Severe",
        "conditions": {"dewpoint_f_min": 68, "temp_f_min": 88, "wind_speed_mph_max": 10, "month_range": (6, 8), "hour_range": (14, 20)},
        "severity": 0.4,
    },
    {
        "name": "Valley Fog Into Severe Transition",
        "conditions": {"visibility_mi_max": 2, "dewpoint_depression_max": 3, "pressure_trend": "falling", "month_range": (3, 5)},
        "severity": 0.5,
    },
    {
        "name": "Winter Ice Storm",
        "conditions": {"temp_f_range": (28, 36), "dewpoint_f_min": 28, "pressure_trend": "falling", "month_range": (11, 2)},
        "severity": 0.7,
    },
    {
        "name": "East TN Heavy Snow",
        "conditions": {"temp_f_range": (30, 40), "dewpoint_f_min": 18, "pressure_mb_min": 1018, "wind_speed_mph_max": 12, "month_range": (11, 3), "hour_range": (0, 8)},
        "severity": 0.8,
    },
    {
        "name": "Appalachian Ice Storm",
        "conditions": {"temp_f_range": (30, 35), "dewpoint_f_min": 18, "dewpoint_depression_max": 15, "pressure_mb_min": 1018, "month_range": (12, 2)},
        "severity": 0.8,
    },
    {
        "name": "Cold Air Damming (CAD)",
        "conditions": {"temp_f_range": (25, 40), "dewpoint_f_min": 18, "wind_direction_range": (0, 60), "pressure_mb_min": 1018, "pressure_mb_max": 1021, "month_range": (11, 3), "hour_range": (0, 8)},
        "severity": 0.6,
    },
]


class HistoricalEngine:
    def __init__(self):
        self.history = {}
        self.max_history = 72

    def ingest(self, station_id, timestamp, **data):
        self.history.setdefault(station_id, []).append({"timestamp": timestamp, **data})
        if len(self.history[station_id]) > self.max_history:
            self.history[station_id] = self.history[station_id][-self.max_history:]

    def _pressure_trend(self, station_id, current_pressure_mb):
        history = self.history.get(station_id, [])
        if len(history) < 3 or current_pressure_mb is None:
            return "steady"
        baseline = history[-3].get("pressure_mb")
        if baseline is None:
            return "steady"
        delta = baseline - current_pressure_mb
        if delta > 3:
            return "falling_fast"
        if delta > 1:
            return "falling"
        return "steady"

    def _month_matches(self, month: int, bounds):
        start, end = bounds
        if start <= end:
            return start <= month <= end
        return month >= start or month <= end

    def score(self, station_id, **current_data):
        ts = parse_timestamp(current_data.get("timestamp"))
        month = ts.month
        hour = ts.hour
        temperature_f = current_data.get("temperature_f")
        dewpoint_f = current_data.get("dewpoint_f")
        wind_direction_deg = current_data.get("wind_direction_deg")
        wind_speed_mph = current_data.get("wind_speed_mph")
        pressure_mb = current_data.get("pressure_mb")
        visibility_mi = current_data.get("visibility_mi")
        pressure_trend = current_data.get("pressure_trend") or self._pressure_trend(station_id, pressure_mb)
        dewpoint_depression = None
        if temperature_f is not None and dewpoint_f is not None:
            dewpoint_depression = temperature_f - dewpoint_f

        best = {"name": None, "score": 0.0, "matched_fraction": 0.0}
        for setup in KNOWN_SEVERE_SETUPS:
            matched = 0
            total = len(setup["conditions"])
            for key, expected in setup["conditions"].items():
                if key == "dewpoint_f_min" and dewpoint_f is not None and dewpoint_f >= expected:
                    matched += 1
                elif key == "wind_direction_range" and wind_direction_deg is not None and expected[0] <= wind_direction_deg <= expected[1]:
                    matched += 1
                elif key == "pressure_trend" and pressure_trend == expected:
                    matched += 1
                elif key == "month_range" and self._month_matches(month, expected):
                    matched += 1
                elif key == "pressure_mb_max" and pressure_mb is not None and pressure_mb <= expected:
                    matched += 1
                elif key == "pressure_mb_min" and pressure_mb is not None and pressure_mb >= expected:
                    matched += 1
                elif key == "wind_speed_mph_min" and wind_speed_mph is not None and wind_speed_mph >= expected:
                    matched += 1
                elif key == "wind_speed_mph_max" and wind_speed_mph is not None and wind_speed_mph <= expected:
                    matched += 1
                elif key == "hour_range" and expected[0] <= hour <= expected[1]:
                    matched += 1
                elif key == "temp_f_min" and temperature_f is not None and temperature_f >= expected:
                    matched += 1
                elif key == "temp_f_range" and temperature_f is not None and expected[0] <= temperature_f <= expected[1]:
                    matched += 1
                elif key == "visibility_mi_max" and visibility_mi is not None and visibility_mi <= expected:
                    matched += 1
                elif key == "dewpoint_depression_max" and dewpoint_depression is not None and dewpoint_depression <= expected:
                    matched += 1
            fraction = matched / total if total else 0.0
            score = fraction * setup["severity"] if fraction >= 0.75 else 0.0
            if score > best["score"]:
                best = {"name": setup["name"], "score": round(score, 4), "matched_fraction": round(fraction, 4)}
        return {"engine": "historical_analog", **best}
