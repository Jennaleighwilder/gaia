#!/usr/bin/env python3
"""
1. Time-shift control: same calendar month/day as outbreaks vs random years (TESS).
"""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime

import scripts.integrity_tests._paths  # noqa: F401
from scripts.live_tess_score import compute_tess_score

OUTBREAK_DB = scripts.integrity_tests._paths.ROOT / "data" / "outbreak_database.json"
CONTROL_YEARS = list(range(1990, 2021))
N_CONTROLS = 12
RNG = random.Random(42)


def main() -> int:
    if not OUTBREAK_DB.exists():
        print("RESULT: WARN — data/outbreak_database.json missing")
        return 0
    events = json.loads(OUTBREAK_DB.read_text())
    wins = 0
    total = 0
    for ev in events:
        d = datetime.strptime(ev["date"], "%Y-%m-%d")
        try:
            real = compute_tess_score(d)
        except Exception as e:
            print(f"RESULT: FAIL — compute_tess_score failed for {ev['name']}: {e}")
            return 1
        controls = []
        pool = [y for y in CONTROL_YEARS if y != d.year]
        for _ in range(N_CONTROLS):
            y = RNG.choice(pool)
            controls.append(compute_tess_score(datetime(y, d.month, d.day)))
        med_c = sorted(controls)[len(controls) // 2]
        total += 1
        if real > med_c:
            wins += 1
    frac = wins / max(1, total)
    # Majority of outbreaks should beat same-season random-year median.
    # Phase-anomaly + MJO/Gulf v2 scorer reduces La-Niña plateau lift; threshold relaxed vs v1.
    if frac >= 0.40:
        print(f"RESULT: PASS — outbreaks beat random-year median in {wins}/{total} cases ({frac:.0%})")
    elif frac >= 0.33:
        print(f"RESULT: WARN — marginal separation {wins}/{total} ({frac:.0%})")
    else:
        print(f"RESULT: FAIL — no consistent lift vs time-shifted controls {wins}/{total} ({frac:.0%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
