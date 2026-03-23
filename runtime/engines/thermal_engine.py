"""
GAIA Thermal Engine
Scores temperature-driven storm fuel and thermal deviation channels.
"""

from __future__ import annotations

import math

from runtime.engines.common import clamp, month_key
from runtime.physics.atmospheric_core import heat_index

THERMAL_CHANNELS = {
    "temp_departure": {"weight": 0.08},
    "dewpoint_depression": {"weight": 0.12},
    "dewpoint_value": {"weight": 0.10},
    "frontal_contrast": {"weight": 0.10},
    "dewpoint_convergence": {"weight": 0.10},
    "temp_trend_3h": {"weight": 0.08},
    "overnight_low_departure": {"weight": 0.08},
    "overnight_cooling_rate": {"weight": 0.0},
    "heat_index": {"weight": 0.06},
    "wet_bulb": {"weight": 0.06},
    "inversion_detection": {"weight": 0.08},
    "surface_heating_rate": {"weight": 0.08},
    "diurnal_range": {"weight": 0.06},
    "freezing_rain_profile": {"weight": 0.10},
    "overnight_dew_frost": {"weight": 0.0},
    "sound_propagation": {"weight": 0.0},
}

EAST_TN_NORMALS = {
    "mar": {"high_f": 58, "low_f": 35, "dewpoint_f": 38},
    "apr": {"high_f": 68, "low_f": 44, "dewpoint_f": 47},
    "may": {"high_f": 76, "low_f": 53, "dewpoint_f": 56},
    "jun": {"high_f": 83, "low_f": 61, "dewpoint_f": 63},
    "jul": {"high_f": 87, "low_f": 65, "dewpoint_f": 67},
    "aug": {"high_f": 86, "low_f": 64, "dewpoint_f": 66},
    "sep": {"high_f": 80, "low_f": 57, "dewpoint_f": 60},
    "oct": {"high_f": 69, "low_f": 45, "dewpoint_f": 48},
    "nov": {"high_f": 58, "low_f": 36, "dewpoint_f": 40},
    "dec": {"high_f": 49, "low_f": 29, "dewpoint_f": 34},
    "jan": {"high_f": 46, "low_f": 27, "dewpoint_f": 31},
    "feb": {"high_f": 50, "low_f": 30, "dewpoint_f": 33},
}


class ThermalEngine:
    def __init__(self):
        self.history = {}
        self.max_history = 72

    def ingest(self, station_id, timestamp, **data):
        self.history.setdefault(station_id, []).append({"timestamp": timestamp, **data})
        if len(self.history[station_id]) > self.max_history:
            self.history[station_id] = self.history[station_id][-self.max_history:]

    def _wet_bulb_f(self, temp_f: float, humidity_pct: float) -> float:
        temp_c = (temp_f - 32.0) * 5.0 / 9.0
        rh = max(1.0, min(100.0, humidity_pct))
        wb_c = (
            temp_c * math.atan(0.151977 * math.sqrt(rh + 8.313659))
            + math.atan(temp_c + rh)
            - math.atan(rh - 1.676331)
            + 0.00391838 * rh ** 1.5 * math.atan(0.023101 * rh)
            - 4.686035
        )
        return wb_c * 9.0 / 5.0 + 32.0

    def score(self, station_id, **current_data):
        timestamp = current_data.get("timestamp")
        month = month_key(timestamp)
        normals = EAST_TN_NORMALS.get(month, EAST_TN_NORMALS["mar"])
        history = self.history.get(station_id, [])
        temperature_f = current_data.get("temperature_f")
        dewpoint_f = current_data.get("dewpoint_f")
        humidity_pct = current_data.get("humidity_pct")
        network_observations = current_data.get("network_observations", [])
        channels = {name: 0.0 for name in THERMAL_CHANNELS}

        if temperature_f is not None:
            channels["temp_departure"] = clamp(abs(temperature_f - normals["high_f"]) / 20.0)

        if temperature_f is not None and dewpoint_f is not None:
            depression = max(0.0, temperature_f - dewpoint_f)
            channels["dewpoint_depression"] = clamp((30.0 - depression) / 25.0)
            channels["dewpoint_value"] = clamp((dewpoint_f - 40.0) / 30.0)

        temps = [o.get("temperature_f") for o in network_observations if o.get("temperature_f") is not None]
        if temperature_f is not None:
            temps.append(temperature_f)
        if len(temps) >= 2:
            channels["frontal_contrast"] = clamp((max(temps) - min(temps)) / 18.0)

        dewpoints = [o.get("dewpoint_f") for o in network_observations if o.get("dewpoint_f") is not None]
        if dewpoint_f is not None:
            dewpoints.append(dewpoint_f)
        if len(dewpoints) >= 2:
            dp_range = max(dewpoints) - min(dewpoints)
            avg_dp = sum(dewpoints) / len(dewpoints)
            closeness = clamp((8.0 - dp_range) / 8.0)
            richness = clamp((avg_dp - 55.0) / 15.0)
            channels["dewpoint_convergence"] = round((closeness * 0.5) + (richness * 0.5), 4)

        if len(history) >= 9 and temperature_f is not None and history[-9].get("temperature_f") is not None:
            delta = temperature_f - history[-9]["temperature_f"]
            channels["temp_trend_3h"] = clamp(abs(delta) / 15.0)

        overnight_low_f = current_data.get("overnight_low_f")
        if overnight_low_f is not None:
            channels["overnight_low_departure"] = clamp(max(0.0, overnight_low_f - normals["low_f"]) / 20.0)
            if dewpoint_f is not None:
                dew_gap = abs(overnight_low_f - dewpoint_f)
                if overnight_low_f <= 38.0:
                    channels["overnight_dew_frost"] = clamp((4.0 - dew_gap) / 4.0)

        if temperature_f is not None and humidity_pct is not None:
            hi = heat_index(temperature_f, humidity_pct)
            channels["heat_index"] = clamp((hi - 90.0) / 20.0)
            wet_bulb = self._wet_bulb_f(temperature_f, humidity_pct)
            channels["wet_bulb"] = clamp((wet_bulb - 65.0) / 20.0)
            sound_speed = 331.3 + (0.606 * ((temperature_f - 32.0) * 5.0 / 9.0)) + (0.0124 * humidity_pct)
            prior_speeds = []
            for item in history[-6:]:
                temp = item.get("temperature_f")
                rh = item.get("humidity_pct")
                if temp is None or rh is None:
                    continue
                prior_speeds.append(331.3 + (0.606 * ((temp - 32.0) * 5.0 / 9.0)) + (0.0124 * rh))
            if prior_speeds:
                anomaly = sound_speed - (sum(prior_speeds) / len(prior_speeds))
                channels["sound_propagation"] = clamp((anomaly + 0.5) / 3.5)
            else:
                channels["sound_propagation"] = clamp(((temperature_f - 68.0) / 22.0) * 0.5 + ((humidity_pct - 60.0) / 35.0) * 0.5)

        inversion_strength_f = current_data.get("inversion_strength_f")
        if inversion_strength_f is not None:
            channels["inversion_detection"] = clamp(inversion_strength_f / 10.0)

        cooling_rate = current_data.get("overnight_cooling_rate_fph")
        if cooling_rate is not None:
            channels["overnight_cooling_rate"] = clamp(cooling_rate / 4.0)

        if len(history) >= 4 and temperature_f is not None:
            older = history[-4].get("temperature_f")
            if older is not None:
                hourly_change = (temperature_f - older) / 1.0
                channels["surface_heating_rate"] = clamp(abs(hourly_change) / 8.0)

        daily_high_f = current_data.get("daily_high_f")
        daily_low_f = current_data.get("daily_low_f")
        if daily_high_f is None and history:
            values = [h.get("temperature_f") for h in history if h.get("temperature_f") is not None]
            if values:
                daily_high_f = max(values)
                daily_low_f = min(values)
        if daily_high_f is not None and daily_low_f is not None and dewpoint_f is not None:
            diurnal_range = daily_high_f - daily_low_f
            tropical_bonus = clamp((dewpoint_f - 60.0) / 10.0)
            channels["diurnal_range"] = clamp(((12.0 - diurnal_range) / 12.0) * tropical_bonus)

        if month in {"nov", "dec", "jan", "feb", "mar"} and temperature_f is not None:
            temp_band = 0.0
            if 28.0 <= temperature_f <= 36.0:
                temp_band = clamp(1.0 - (abs(temperature_f - 32.0) / 8.0))
            elif 36.0 < temperature_f <= 40.0:
                temp_band = clamp((40.0 - temperature_f) / 4.0)

            saturation = 0.0
            if dewpoint_f is not None:
                saturation = clamp((15.0 - abs(temperature_f - dewpoint_f)) / 15.0)

            cooling_signal = 0.0
            if len(history) >= 4 and history[-4].get("temperature_f") is not None:
                older = history[-4]["temperature_f"]
                cooling_signal = clamp(max(0.0, older - temperature_f) / 10.0)

            pressure_support = 0.0
            pressure_mb = current_data.get("pressure_mb")
            if pressure_mb is not None:
                pressure_support = clamp((pressure_mb - 1016.0) / 8.0)

            channels["freezing_rain_profile"] = round(
                (temp_band * 0.5) + (saturation * 0.2) + (cooling_signal * 0.2) + (pressure_support * 0.1),
                4,
            )

        weighted = sum(channels[name] * THERMAL_CHANNELS[name]["weight"] for name in channels)
        severe_count = sum(
            1
            for name, value in channels.items()
            if name not in {"overnight_dew_frost", "sound_propagation"} and value >= 0.8
        )
        if severe_count:
            weighted += min(0.4, severe_count * 0.07)
        if max(channels.values()) > 0.8:
            weighted = max(weighted, 0.3)
        dominant = sorted(channels.items(), key=lambda item: item[1], reverse=True)[:3]
        return {
            "engine": "thermal",
            "score": round(clamp(weighted), 4),
            "channels": channels,
            "dominant_channels": dominant,
        }
