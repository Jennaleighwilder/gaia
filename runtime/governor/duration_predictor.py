"""
GAIA Duration Predictor
Classifies likely event duration from pressure tempo.
"""

from __future__ import annotations


class DurationPredictor:
    def classify_duration(
        self,
        pressure_drop_rate_mbph: float | None,
        total_drop_mb: float | None,
        drop_window_hours: float | None,
    ) -> str:
        rate = pressure_drop_rate_mbph or 0.0
        total_drop = total_drop_mb or 0.0
        window = drop_window_hours or 0.0

        if window <= 1.0 and rate >= 1.5:
            return "BRIEF"
        if window >= 12.0 or (window >= 6.0 and rate <= 0.4 and total_drop >= 3.0):
            return "PROLONGED"
        if window >= 4.0 or (window >= 2.0 and rate <= 0.8 and total_drop >= 2.5):
            return "SUSTAINED"
        if window >= 1.0 or total_drop >= 2.0:
            return "MODERATE"
        return "BRIEF"

    def format_warning(self, duration_class: str, event_type: str = "weather event") -> str:
        label = event_type.upper()
        if duration_class == "PROLONGED":
            return f"LONG-DURATION {label} EXPECTED. Prepare for extended impact."
        if duration_class == "SUSTAINED":
            return f"SUSTAINED {label} LIKELY. Prepare for several hours of impact."
        if duration_class == "MODERATE":
            return f"MODERATE-DURATION {label} EXPECTED. Prepare for a few hours of impact."
        return f"INTENSE BUT SHORT-LIVED {label} APPROACHING. Take immediate shelter."
