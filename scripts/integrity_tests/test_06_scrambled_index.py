#!/usr/bin/env python3
"""
6. Scrambled / neutral indices: TESS should collapse when layers are forced neutral.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

import scripts.integrity_tests._paths  # noqa: F401
from scripts.live_tess_score import compute_tess_score

OUTBREAK_DB = scripts.integrity_tests._paths.ROOT / "data" / "outbreak_database.json"
SAMPLE = 8
RNG_SEED = 7


def main() -> int:
    if not OUTBREAK_DB.exists():
        print("RESULT: WARN — outbreak_database.json missing")
        return 0
    events = json.loads(OUTBREAK_DB.read_text())
    # Deterministic subsample
    step = max(1, len(events) // SAMPLE)
    picked = events[::step][:SAMPLE]
    neutrals: list[float] = []
    reals: list[float] = []
    for ev in picked:
        d = datetime.strptime(ev["date"], "%Y-%m-%d")
        try:
            neutrals.append(compute_tess_score(d, neutral=True))
            reals.append(compute_tess_score(d, neutral=False))
        except Exception as e:
            print(f"RESULT: FAIL — {e}")
            return 1
    mean_n = sum(neutrals) / len(neutrals)
    mean_r = sum(reals) / len(reals)
    if mean_n < 0.15 and mean_r > mean_n + 0.15:
        print(
            f"RESULT: PASS — neutral mean {mean_n:.3f} << real mean {mean_r:.3f} "
            f"({len(picked)} outbreak dates)"
        )
    elif mean_n < 0.25 and mean_r > mean_n:
        print(f"RESULT: WARN — neutral {mean_n:.3f} vs real {mean_r:.3f} (weaker separation)")
    else:
        print(
            f"RESULT: FAIL — index values may not be driving score "
            f"(neutral {mean_n:.3f}, real {mean_r:.3f})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
