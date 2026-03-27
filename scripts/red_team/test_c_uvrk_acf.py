#!/usr/bin/env python3
"""
RED TEAM C: Tornado-outbreak monthly series autocorrelation vs hurricane-domain UVRK story.
live_tess_score uses theta=0.92 on volatility recursion (not uvrk_engine.KAPPA=0.15).
Explicit domain justification gap for reviewers.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime

import scripts.red_team._paths  # noqa: F401

ROOT = scripts.red_team._paths.ROOT
OUTBREAK_DB = ROOT / "data" / "outbreak_database.json"


def _pearson_lag(series: list[float], lag: int) -> float:
    if len(series) <= lag or lag < 1:
        return 0.0
    x = series[:-lag]
    y = series[lag:]
    n = len(x)
    if n < 2:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yj - my) for xi, yj in zip(x, y))
    dx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    dy = math.sqrt(sum((yj - my) ** 2 for yj in y))
    return num / (dx * dy) if dx > 0 and dy > 0 else 0.0


def main() -> int:
    print("=== RED TEAM C: UVRK-1 / VOLATILITY PARAMETERS VS TORNADO MONTHLY LABELS ===")
    print()
    print("GAIA TESS (live_tess_score.uvrk1_instability) uses:")
    print("  predicted_vol = 0.92 * current_vol + 0.08 * 0.15 * |probit|")
    print("  i.e. theta≈0.92 on the volatility recursion term (hurricane literature often cited).")
    print("runtime/engines/uvrk_engine.py uses THETA=0.92, KAPPA=0.15 (met station volatility).")
    print()

    if not OUTBREAK_DB.exists():
        print("RESULT: FAIL — outbreak_database.json missing")
        return 1
    with open(OUTBREAK_DB) as f:
        outbreaks = json.load(f)
    ob_ym = {o["date"][:7] for o in outbreaks}

    labels: list[float] = []
    for year in range(1990, 2025):
        for month in range(1, 13):
            ym = f"{year}-{month:02d}"
            labels.append(1.0 if ym in ob_ym else 0.0)

    acf1 = _pearson_lag(labels, 1)
    acf12 = _pearson_lag(labels, 12)

    print("Binary outbreak-month series (1990-01 … 2024-12):")
    print(f"  Lag-1 ACF (month-to-month):  {acf1:.3f}")
    print(f"  Lag-12 ACF (seasonal):        {acf12:.3f}")
    print()
    print("Interpretation for reviewers:")
    print("  • Low lag-1 ACF ⇒ outbreaks are rare independent draws across months;")
    print("    a heavy monthly persistence kernel (hurricane annual count) is a weak analogy.")
    print("  • Any theta/kappa used inside TESS should be sensitivity-tested or refit to")
    print("    a proper scoring rule on held-out outbreak months, not asserted from hurricanes.")
    print()
    print("RESULT: PASS — diagnostics printed; explicit refit still TODO (not scipy-dependent).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
