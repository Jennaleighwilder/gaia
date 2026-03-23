"""
Engine motion correlation utilities.

Measures whether alarm engines are moving together over a recent window.
Elevated but static conditions should score low. Coordinated acceleration
should score high.
"""

from __future__ import annotations


def engine_correlation(score_timeline: list[dict], alarm_engines: list[str], window: int = 4) -> float:
    """
    Compute how strongly engine score changes agree over a recent window.

    Returns:
        0.0 -> engines are flat or moving independently
        1.0 -> engines are moving together in the same direction
    """
    if len(score_timeline) < window + 1 or not alarm_engines:
        return 0.0

    recent = score_timeline[-(window + 1):]
    deltas = {engine: [] for engine in alarm_engines}

    for idx in range(1, len(recent)):
        previous = recent[idx - 1]
        current = recent[idx]
        for engine in alarm_engines:
            prev_score = previous.get(engine, 0.0) or 0.0
            curr_score = current.get(engine, 0.0) or 0.0
            deltas[engine].append(curr_score - prev_score)

    n_steps = len(next(iter(deltas.values()), []))
    if n_steps == 0:
        return 0.0

    agreement_scores = []
    total_engines = len(alarm_engines)

    for step in range(n_steps):
        rising = 0
        falling = 0
        for engine in alarm_engines:
            delta = deltas[engine][step]
            if delta > 0.02:
                rising += 1
            elif delta < -0.02:
                falling += 1

        total_active = rising + falling
        if total_active == 0:
            agreement_scores.append(0.0)
            continue

        dominant = max(rising, falling)
        agreement = dominant / total_active
        activity = total_active / total_engines
        agreement_scores.append(agreement * activity)

    if not agreement_scores:
        return 0.0

    if len(agreement_scores) >= 2:
        earlier = agreement_scores[:-2]
        earlier_avg = (sum(earlier) / len(earlier)) if earlier else 0.0
        weighted = (
            (agreement_scores[-1] * 0.5)
            + (agreement_scores[-2] * 0.3)
            + (earlier_avg * 0.2)
        )
    else:
        weighted = sum(agreement_scores) / len(agreement_scores)

    return round(min(1.0, weighted), 4)
