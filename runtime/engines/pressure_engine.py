"""
GAIA Pressure Engine
Monitors barometric pressure for severe weather signatures.
Cloned from West-OS murderlock pattern-matching architecture.
"""

PRESSURE_SIGNATURES = {
    "rapid_drop": {
        "description": "Pressure dropping > 3mb in 3 hours",
        "weight": 0.8,
    },
    "deep_low": {
        "description": "Pressure below 1000mb",
        "weight": 0.6,
    },
    "pressure_gradient": {
        "description": "Pressure difference > 4mb between nearby stations",
        "weight": 0.7,
    },
    "oscillation": {
        "description": "Pressure oscillating rapidly",
        "weight": 0.5,
    },
    "falling_tendency": {
        "description": "Steady falling pressure over 6+ hours",
        "weight": 0.4,
    },
    "oscillation_variance": {
        "description": "Pressure variance rising over short window",
        "weight": 0.0,
    },
    "visibility_trend": {
        "description": "Visibility improving while pressure falls",
        "weight": 0.0,
    },
    "wind_persistence_break": {
        "description": "Locked wind regime breaking under falling pressure",
        "weight": 0.0,
    },
}


class PressureEngine:
    """
    Scores atmospheric pressure anomaly from 0.0 (normal) to 1.0 (extreme).
    Maintains a rolling history of observations per station/region.
    """

    def __init__(self):
        self.history = {}
        self.max_history = 72

    def ingest(
        self,
        station_id: str,
        timestamp: str,
        pressure_mb: float,
        visibility_mi: float | None = None,
        wind_direction_deg: float | None = None,
    ):
        if station_id not in self.history:
            self.history[station_id] = []
        self.history[station_id].append(
            {
                "timestamp": timestamp,
                "pressure_mb": pressure_mb,
                "visibility_mi": visibility_mi,
                "wind_direction_deg": wind_direction_deg,
            }
        )
        if len(self.history[station_id]) > self.max_history:
            self.history[station_id] = self.history[station_id][-self.max_history:]

    def score(
        self,
        station_id: str,
        current_pressure_mb: float,
        pressure_trend: str | None = None,
        network_pressures: list[float] | None = None,
        visibility_mi: float | None = None,
        wind_direction_deg: float | None = None,
    ) -> dict:
        history = self.history.get(station_id, [])
        matched = []
        max_score = 0.0
        pressure_drop_rate = 0.0
        max_drop_mb = 0.0
        drop_window_hours = 0.0

        if current_pressure_mb is not None and current_pressure_mb < 1000:
            severity = min(1.0, (1000 - current_pressure_mb) / 20.0)
            weighted = severity * PRESSURE_SIGNATURES["deep_low"]["weight"]
            matched.append(("deep_low", weighted))
            max_score = max(max_score, weighted)

        if len(history) >= 9:
            pressure_3h_ago = history[-9].get("pressure_mb")
            if pressure_3h_ago is not None and current_pressure_mb is not None:
                drop = pressure_3h_ago - current_pressure_mb
                if drop > 3.0:
                    severity = min(1.0, drop / 10.0)
                    weighted = severity * PRESSURE_SIGNATURES["rapid_drop"]["weight"]
                    matched.append(("rapid_drop", weighted))
                    max_score = max(max_score, weighted)
                if drop > max_drop_mb:
                    max_drop_mb = drop
                    pressure_drop_rate = max_drop_mb / 3.0
                    drop_window_hours = 3.0

        if len(history) >= 18:
            pressure_6h_ago = history[-18].get("pressure_mb")
            if pressure_6h_ago is not None and current_pressure_mb is not None:
                drop = pressure_6h_ago - current_pressure_mb
                if drop > 2.0:
                    severity = min(1.0, drop / 8.0)
                    weighted = severity * PRESSURE_SIGNATURES["falling_tendency"]["weight"]
                    matched.append(("falling_tendency", weighted))
                    max_score = max(max_score, weighted)
                if drop > max_drop_mb:
                    max_drop_mb = drop
                    pressure_drop_rate = max_drop_mb / 6.0
                    drop_window_hours = 6.0

        trend_weights = {
            "falling": 0.45,
            "falling_fast": 0.7,
        }
        if pressure_trend in trend_weights:
            weighted = trend_weights[pressure_trend]
            matched.append(("falling_tendency", weighted))
            max_score = max(max_score, weighted)

        nearby = [p for p in (network_pressures or []) if p is not None]
        if current_pressure_mb is not None and nearby:
            gradient = max(abs(current_pressure_mb - other) for other in nearby)
            if gradient >= 1.5:
                severity = min(1.0, gradient / 4.0)
                weighted = severity * PRESSURE_SIGNATURES["pressure_gradient"]["weight"]
                matched.append(("pressure_gradient", weighted))
                max_score = max(max_score, weighted)

        if len(history) >= 6:
            recent = [h.get("pressure_mb") for h in history[-6:] if h.get("pressure_mb") is not None]
            if len(recent) >= 6:
                diffs = [recent[i + 1] - recent[i] for i in range(len(recent) - 1)]
                sign_changes = sum(1 for i in range(len(diffs) - 1) if diffs[i] * diffs[i + 1] < 0)
                if sign_changes >= 3:
                    severity = min(1.0, sign_changes / 5.0)
                    weighted = severity * PRESSURE_SIGNATURES["oscillation"]["weight"]
                    matched.append(("oscillation", weighted))
                    max_score = max(max_score, weighted)
                mean_pressure = sum(recent) / len(recent)
                variance = sum((value - mean_pressure) ** 2 for value in recent) / len(recent)
                stddev = variance ** 0.5
                if stddev >= 0.5:
                    severity = min(1.0, stddev / 1.6)
                    weighted = severity * PRESSURE_SIGNATURES["oscillation_variance"]["weight"]
                    matched.append(("oscillation_variance", weighted))
                    max_score = max(max_score, weighted)

        if visibility_mi is not None and pressure_trend in {"falling", "falling_fast"} and len(history) >= 3:
            prior_visibility = history[-3].get("visibility_mi")
            if prior_visibility is not None:
                visibility_delta = visibility_mi - prior_visibility
                if visibility_delta > 1.0:
                    severity = min(1.0, visibility_delta / 6.0)
                    weighted = severity * PRESSURE_SIGNATURES["visibility_trend"]["weight"]
                    matched.append(("visibility_trend", weighted))
                    max_score = max(max_score, weighted)

        if wind_direction_deg is not None and len(history) >= 18:
            prior_dirs = [item.get("wind_direction_deg") for item in history[-18:] if item.get("wind_direction_deg") is not None]
            if len(prior_dirs) >= 12:
                spread = max(prior_dirs) - min(prior_dirs)
                shift = min(abs(wind_direction_deg - prior_dirs[-1]), 360 - abs(wind_direction_deg - prior_dirs[-1]))
                if spread <= 35.0 and shift >= 45.0:
                    severity = min(1.0, shift / 120.0)
                    weighted = severity * PRESSURE_SIGNATURES["wind_persistence_break"]["weight"]
                    matched.append(("wind_persistence_break", weighted))
                    max_score = max(max_score, weighted)

        return {
            "engine": "pressure",
            "score": round(min(1.0, max_score), 4),
            "matched_signatures": matched,
            "history_depth": len(history),
            "current_pressure_mb": current_pressure_mb,
            "pressure_drop_rate_mbph": round(pressure_drop_rate, 4),
            "max_drop_mb": round(max_drop_mb, 4),
            "drop_window_hours": round(drop_window_hours, 4),
        }
