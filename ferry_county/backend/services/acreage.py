from __future__ import annotations


def calculate_acres(miles: float, buffer_ft: float = 15.0) -> float:
    """
    Corridor acres from centerline miles and side buffer (USDA-style strip area).
    width_ft = buffer each side * 2; sq ft per mile of corridor = 5280 * width_ft; acres = sq_ft / 43560.
    """
    width_ft = buffer_ft * 2.0
    sq_ft_per_mile = 5280.0 * width_ft
    return float(miles) * sq_ft_per_mile / 43560.0
