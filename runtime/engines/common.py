from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Iterable


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def safe_mean(values: Iterable[float]) -> float:
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else 0.0


def parse_timestamp(timestamp: str | None) -> datetime:
    if not timestamp:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def month_key(timestamp: str | None) -> str:
    return parse_timestamp(timestamp).strftime("%b").lower()


def circular_diff_deg(a: float | None, b: float | None) -> float:
    if a is None or b is None:
        return 0.0
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def signed_circular_delta_deg(current: float | None, previous: float | None) -> float:
    if current is None or previous is None:
        return 0.0
    return ((current - previous + 540.0) % 360.0) - 180.0


def circular_spread_deg(angles: list[float]) -> float:
    if not angles:
        return 0.0
    sin_sum = sum(math.sin(math.radians(a)) for a in angles)
    cos_sum = sum(math.cos(math.radians(a)) for a in angles)
    r = math.sqrt(sin_sum ** 2 + cos_sum ** 2) / len(angles)
    return (1.0 - r) * 180.0
