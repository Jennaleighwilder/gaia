"""
GAIA Frozen Physics Core
These equations are laws of physics. They do not change.
No engine modifies them. No learning adjusts them.
Every engine that needs physics calls these functions.
"""

import math


def saturation_vapor_pressure(temp_c: float) -> float:
    """August-Roche-Magnus approximation in hPa."""
    return 6.112 * math.exp((17.67 * temp_c) / (temp_c + 243.5))


def dewpoint_depression(temp_c: float, dewpoint_c: float) -> float:
    """Difference between temperature and dewpoint in Celsius."""
    return temp_c - dewpoint_c


def lifted_condensation_level(temp_c: float, dewpoint_c: float) -> float:
    """Approximate LCL in meters."""
    return 125.0 * (temp_c - dewpoint_c)


def dry_adiabatic_lapse_rate() -> float:
    """Dry adiabatic lapse rate in C/km."""
    return 9.8


def fahrenheit_to_celsius(f: float) -> float:
    return (f - 32.0) * 5.0 / 9.0


def celsius_to_fahrenheit(c: float) -> float:
    return c * 9.0 / 5.0 + 32.0


def mb_to_inhg(mb: float) -> float:
    return mb * 0.02953


def knots_to_mph(kts: float) -> float:
    return kts * 1.15078


def wind_chill(temp_f: float, wind_mph: float) -> float:
    if temp_f > 50 or wind_mph < 3:
        return temp_f
    return (
        35.74
        + 0.6215 * temp_f
        - 35.75 * (wind_mph ** 0.16)
        + 0.4275 * temp_f * (wind_mph ** 0.16)
    )


def heat_index(temp_f: float, rh_pct: float) -> float:
    if temp_f < 80:
        return temp_f
    return (
        -42.379
        + 2.04901523 * temp_f
        + 10.14333127 * rh_pct
        - 0.22475541 * temp_f * rh_pct
        - 0.00683783 * temp_f ** 2
        - 0.05481717 * rh_pct ** 2
        + 0.00122874 * temp_f ** 2 * rh_pct
        + 0.00085282 * temp_f * rh_pct ** 2
        - 0.00000199 * temp_f ** 2 * rh_pct ** 2
    )


def pressure_altitude(pressure_mb: float) -> float:
    return 44330.0 * (1.0 - (pressure_mb / 1013.25) ** 0.1903)


def bulk_shear(u_sfc: float, v_sfc: float, u_6km: float, v_6km: float) -> float:
    du = u_6km - u_sfc
    dv = v_6km - v_sfc
    return math.sqrt(du ** 2 + dv ** 2)


def storm_relative_helicity(shear_magnitude: float, storm_motion: float, mean_wind_dir_change_deg: float) -> float:
    dir_rad = math.radians(mean_wind_dir_change_deg)
    return shear_magnitude * storm_motion * math.sin(dir_rad)
