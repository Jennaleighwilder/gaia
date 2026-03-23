"""
Seasonal overlay for East Tennessee severe weather.

East TN has strong seasonal patterns. Same thresholds year-round is wrong.
Pressure acceleration 0.2 in July ≠ 0.2 in January.
"""

from __future__ import annotations

from typing import Any, Optional

# East TN seasonal definitions
SPRING_MONTHS = (3, 4, 5)
SUMMER_MONTHS = (6, 7, 8)
FALL_MONTHS = (9, 10, 11)
WINTER_MONTHS = (12, 1, 2)

EAST_TN_PROFILES = {
    "SPRING": {
        "months": SPRING_MONTHS,
        "severe_probability": "HIGH",
        "dominant_threats": ["tornado", "thunderstorm_wind", "hail"],
        "siren_sensitivity": 1.1,
        "moisture_baseline": "moderate-high",
        "instability_baseline": "high",
        "false_alarm_risk": "LOW",
        "seasonal_context": "SPRING — peak tornado and thunderstorm wind season",
        "use_winter_engines_only": False,
    },
    "SUMMER": {
        "months": SUMMER_MONTHS,
        "severe_probability": "MODERATE",
        "dominant_threats": ["thunderstorm_wind", "flash_flood"],
        "siren_sensitivity": 0.8,
        "moisture_baseline": "high",
        "instability_baseline": "moderate",
        "false_alarm_risk": "HIGH",
        "seasonal_context": "SUMMER — elevated false alarm risk, afternoon convection common in East TN",
        "use_winter_engines_only": False,
    },
    "FALL": {
        "months": FALL_MONTHS,
        "severe_probability": "LOW-MODERATE",
        "dominant_threats": ["thunderstorm_wind", "flood"],
        "siren_sensitivity": 0.9,
        "moisture_baseline": "decreasing",
        "instability_baseline": "moderate",
        "false_alarm_risk": "MODERATE",
        "seasonal_context": "FALL — transition season, mixed signals",
        "use_winter_engines_only": False,
    },
    "WINTER": {
        "months": WINTER_MONTHS,
        "severe_probability": "LOW",
        "convective_probability": "LOW",
        "dominant_threats": ["winter_storm", "ice", "flooding"],
        "siren_sensitivity": 0.0,
        "moisture_baseline": "low",
        "instability_baseline": "low",
        "false_alarm_risk": "LOW",
        "seasonal_context": "WINTER — snow/ice events, different physics, no convection",
        "use_winter_engines_only": True,
    },
}


def get_seasonal_profile(month: int, county: Optional[str] = None) -> dict[str, Any]:
    """
    Return seasonal profile for East Tennessee given month (1-12).
    county: optional for future multi-region support.
    """
    if month in SPRING_MONTHS:
        return dict(EAST_TN_PROFILES["SPRING"], season_name="SPRING")
    if month in SUMMER_MONTHS:
        return dict(EAST_TN_PROFILES["SUMMER"], season_name="SUMMER")
    if month in FALL_MONTHS:
        return dict(EAST_TN_PROFILES["FALL"], season_name="FALL")
    if month in WINTER_MONTHS:
        return dict(EAST_TN_PROFILES["WINTER"], season_name="WINTER")
    return dict(EAST_TN_PROFILES["SPRING"], season_name="SPRING")  # fallback
