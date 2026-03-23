"""
GAIA Instability Engine
Scores convective energy and tracks atmosphere phase transitions.
Also carries a winter-mode pathway for cold-season snow/ice setup detection.
"""

from __future__ import annotations

from runtime.engines.common import clamp, month_key

INSTABILITY_CHANNELS = {
    "cape_value": {"weight": 0.30},
    "cin_erosion": {"weight": 0.20},
    "surface_based_estimate": {"weight": 0.20},
    "cloud_development": {"weight": 0.15},
    "trigger_proximity": {"weight": 0.15},
    "daytime_heating_rate": {"weight": 0.0},
    "sounding_cape": {"weight": 0.35},
    "sounding_cin": {"weight": 0.15},
    "cloud_type_progression": {"weight": 0.0},
    "pressure_acceleration": {"weight": 0.0},
    "pressure_temperature_divergence": {"weight": 0.0},
    "sky_cover_trend": {"weight": 0.0},
}


class InstabilityEngine:
    def __init__(self):
        self.history = {}
        self.phase_state = {}
        self.max_history = 72

    def ingest(self, station_id, timestamp, **data):
        self.history.setdefault(station_id, []).append({"timestamp": timestamp, **data})
        if len(self.history[station_id]) > self.max_history:
            self.history[station_id] = self.history[station_id][-self.max_history:]

    def _cloud_score(self, text_description: str | None) -> float:
        if not text_description:
            return 0.0
        low = text_description.lower()
        if "cumulonimbus" in low or "towering cumulus" in low:
            return 1.0
        if "cumulus" in low:
            return 0.5
        if "clear" in low or "fair" in low:
            return 0.0
        return 0.1

    def _surface_instability(self, temperature_f: float | None, dewpoint_f: float | None) -> float:
        if temperature_f is None or dewpoint_f is None:
            return 0.0
        spread = max(0.0, temperature_f - dewpoint_f)
        index = (temperature_f - 70.0) / 20.0 + (20.0 - spread) / 20.0
        return clamp(index / 2.0)

    def _cloud_rank(self, text_description: str | None) -> float:
        if not text_description:
            return 0.0
        low = text_description.lower()
        if "cumulonimbus" in low or " cb" in f" {low} ":
            return 4.0
        if "towering cumulus" in low or " tcu" in f" {low} ":
            return 3.0
        if "altocumulus" in low or " ac" in f" {low} ":
            return 2.0
        if "cirrus" in low or " ci" in f" {low} ":
            return 1.0
        if "cumulus" in low:
            return 2.5
        return 0.0

    def _determine_phase(self, score: float, cin_score: float, trigger_score: float, cloud_score: float) -> str:
        if score < 0.15 and cin_score < 0.2:
            return "HOMEOSTASIS"
        if score < 0.4 and trigger_score < 0.2:
            return "DRIFT"
        if trigger_score >= 0.3 and cloud_score < 0.5:
            return "INSULT"
        if cloud_score >= 0.5 and score >= 0.5:
            return "PROPAGATION"
        if score >= 0.75:
            return "STASIS"
        if score >= 0.45:
            return "COMPENSATION"
        return "COLLAPSE"

    def _winter_mode_score(self, history, current_data, cloud_score: float) -> float:
        temperature_f = current_data.get("temperature_f")
        dewpoint_f = current_data.get("dewpoint_f")
        pressure_mb = current_data.get("pressure_mb")
        wind_direction_deg = current_data.get("wind_direction_deg")
        humidity_pct = current_data.get("humidity_pct")

        if temperature_f is None:
            return 0.0

        temp_band = 0.0
        if 28.0 <= temperature_f <= 36.0:
            temp_band = clamp(1.0 - (abs(temperature_f - 32.0) / 8.0))
        elif 36.0 < temperature_f <= 40.0:
            temp_band = clamp((40.0 - temperature_f) / 4.0)

        saturation = 0.0
        if dewpoint_f is not None:
            saturation = clamp((15.0 - abs(temperature_f - dewpoint_f)) / 15.0)
        elif humidity_pct is not None:
            saturation = clamp((humidity_pct - 55.0) / 35.0)

        pressure_support = 0.0
        if pressure_mb is not None:
            pressure_support = clamp((pressure_mb - 1016.0) / 8.0)

        cooling_signal = 0.0
        if len(history) >= 4 and history[-4].get("temperature_f") is not None:
            older = history[-4]["temperature_f"]
            cooling_signal = clamp(max(0.0, older - temperature_f) / 12.0)

        northerly_flow = 0.0
        if wind_direction_deg is not None and (wind_direction_deg <= 60.0 or wind_direction_deg >= 300.0):
            northerly_flow = 1.0

        winter_score = (
            (temp_band * 0.35)
            + (saturation * 0.20)
            + (pressure_support * 0.20)
            + (cooling_signal * 0.15)
            + (max(cloud_score, northerly_flow) * 0.10)
        )
        return round(clamp(winter_score), 4)

    def score(self, station_id, **current_data):
        history = self.history.get(station_id, [])
        channels = {name: 0.0 for name in INSTABILITY_CHANNELS}

        upper_air = current_data.get("upper_air") or {}
        sounding_cape = upper_air.get("sbcape_jkg")
        if sounding_cape is None:
            sounding_cape = upper_air.get("mlcape_jkg")
        sounding_cin = upper_air.get("sbcin_jkg")
        if sounding_cin is None:
            sounding_cin = upper_air.get("mlcin_jkg")

        cape = current_data.get("cape_jkg")
        cin = current_data.get("cin_jkg")
        text_description = current_data.get("text_description")
        trigger_events = current_data.get("trigger_events", [])
        month = month_key(current_data.get("timestamp"))
        temperature_f = current_data.get("temperature_f")
        dewpoint_f = current_data.get("dewpoint_f")

        if sounding_cape is not None:
            if sounding_cape < 500:
                channels["sounding_cape"] = 0.1
            elif sounding_cape < 1500:
                channels["sounding_cape"] = 0.3
            elif sounding_cape < 3000:
                channels["sounding_cape"] = 0.6
            elif sounding_cape < 5000:
                channels["sounding_cape"] = 0.85
            else:
                channels["sounding_cape"] = 1.0

        if sounding_cin is not None:
            cin_abs = abs(sounding_cin)
            if cin_abs < 50:
                channels["sounding_cin"] = 0.7
            elif cin_abs < 150:
                channels["sounding_cin"] = 0.4
            else:
                channels["sounding_cin"] = 0.1

        if cape is not None:
            channels["cape_value"] = clamp(cape / 3000.0)

        if cin is not None:
            if len(history) >= 2 and history[-2].get("cin_jkg") is not None:
                previous = abs(history[-2]["cin_jkg"])
                current = abs(cin)
                channels["cin_erosion"] = clamp(max(0.0, previous - current) / 100.0)
            elif abs(cin) <= 25:
                channels["cin_erosion"] = 0.7

        winter_mode = month in {"nov", "dec", "jan", "feb", "mar"} and temperature_f is not None and temperature_f < 40.0
        if winter_mode:
            channels["surface_based_estimate"] = self._winter_mode_score(history, current_data, self._cloud_score(text_description))
        else:
            channels["surface_based_estimate"] = self._surface_instability(temperature_f, dewpoint_f)
        channels["cloud_development"] = self._cloud_score(text_description)

        if trigger_events:
            channels["trigger_proximity"] = clamp(len(trigger_events) / 3.0)
        elif current_data.get("trigger_score") is not None:
            channels["trigger_proximity"] = clamp(current_data["trigger_score"])

        heating_rate = current_data.get("daytime_heating_rate_fph")
        if heating_rate is not None and heating_rate > 0:
            channels["daytime_heating_rate"] = clamp(min(1.0, heating_rate / 6.0))

        # pressure_acceleration > 0.3 (second derivative of pressure) -> instability signal
        p_acc = current_data.get("pressure_acceleration")
        if p_acc is not None and p_acc > 0:
            channels["pressure_acceleration"] = clamp(min(1.0, p_acc / 0.5))
        # PTI: strong frontal signal when temp change >> pressure change
        pti = current_data.get("pressure_temperature_divergence_index")
        if pti is not None and pti > 0:
            channels["pressure_temperature_divergence"] = clamp(min(1.0, pti / 5.0))
        # sky_cover_trend > 1.5/hr = rapid cloud build
        sky_tr = current_data.get("sky_cover_trend")
        if sky_tr is not None and sky_tr > 0:
            channels["sky_cover_trend"] = clamp(min(1.0, sky_tr / 3.0))

        current_cloud_rank = self._cloud_rank(text_description)
        prior_cloud_ranks = [self._cloud_rank(item.get("text_description")) for item in history[-4:]]
        prior_cloud_ranks = [value for value in prior_cloud_ranks if value > 0.0]
        if current_cloud_rank > 0.0 and prior_cloud_ranks:
            prior_rank = max(prior_cloud_ranks)
            if current_cloud_rank > prior_rank:
                channels["cloud_type_progression"] = clamp(
                    ((current_cloud_rank - prior_rank) / 3.0) + ((current_cloud_rank - 1.0) / 8.0)
                )

        weighted = sum(channels[name] * INSTABILITY_CHANNELS[name]["weight"] for name in channels)
        if channels["sounding_cape"] > 0:
            weighted += channels["sounding_cape"] * 0.25
        if channels["sounding_cin"] > 0:
            weighted += channels["sounding_cin"] * 0.08
        if not winter_mode and channels["cape_value"] >= 0.7 and channels["cin_erosion"] >= 0.5:
            weighted += 0.18
        if channels["trigger_proximity"] >= 0.3 and channels["surface_based_estimate"] >= 0.4:
            weighted += 0.08
        if winter_mode and channels["surface_based_estimate"] >= 0.5:
            weighted += 0.18
        if sounding_cape is not None and sounding_cin is not None and sounding_cape >= 1500 and abs(sounding_cin) <= 50:
            weighted += 0.12
        phase = self._determine_phase(
            weighted,
            max(channels["cin_erosion"], channels["sounding_cin"]),
            channels["trigger_proximity"],
            channels["cloud_development"],
        )
        previous_phase = self.phase_state.get(station_id)
        phase_transition = None
        if previous_phase and previous_phase != phase:
            phase_transition = {"from": previous_phase, "to": phase}
        self.phase_state[station_id] = phase
        return {
            "engine": "instability",
            "score": round(clamp(weighted), 4),
            "channels": channels,
            "phase": phase,
            "phase_transition": phase_transition,
        }
