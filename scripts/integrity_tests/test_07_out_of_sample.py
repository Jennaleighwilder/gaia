#!/usr/bin/env python3
"""
7. Out-of-sample: recent outbreaks (post-2022) not used for any offline fitting here,
   but scored with the same historical TESS pipeline.
"""
from __future__ import annotations

import sys
from datetime import datetime

import scripts.integrity_tests._paths  # noqa: F401
from scripts.live_tess_score import compute_tess_score

# Held-out style list (dates after typical static index cutoffs in docs).
HOLDOUTS = [
    ("Rolling Fork MS", "2023-03-24"),
    ("Little Rock AR", "2023-03-31"),
    ("Perryton TX", "2023-06-15"),
    ("Clarksville TN", "2023-12-09"),
    ("Hollister OK", "2024-05-20"),
]
THRESH = 0.28


def main() -> int:
    ok = 0
    scores: list[tuple[str, float]] = []
    for name, ds in HOLDOUTS:
        d = datetime.strptime(ds, "%Y-%m-%d")
        try:
            s = compute_tess_score(d)
        except Exception as e:
            print(f"RESULT: FAIL — {name}: {e}")
            return 1
        scores.append((name, s))
        if s >= THRESH:
            ok += 1
    for name, s in scores:
        print(f"  {name}: TESS={s:.3f}")
    if ok >= 4:
        print(f"RESULT: PASS — {ok}/{len(HOLDOUTS)} holdouts >= {THRESH}")
    elif ok >= 3:
        print(f"RESULT: WARN — {ok}/{len(HOLDOUTS)} holdouts >= {THRESH}")
    else:
        print(f"RESULT: FAIL — {ok}/{len(HOLDOUTS)} holdouts >= {THRESH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
