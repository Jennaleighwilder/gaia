#!/usr/bin/env python3
"""
2. Global false-alarm rate: P(TESS > 0.80) on random (year, month) away from outbreaks.

Historical TESS is monthly; each independent draw is a unique (y, m) with day fixed
to 15. Excludes any month that contains an outbreak date ±14 days.
"""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta

import scripts.integrity_tests._paths  # noqa: F401
from scripts.live_tess_score import compute_tess_score

ROOT = scripts.integrity_tests._paths.ROOT
OUTBREAK_DB = ROOT / "data" / "outbreak_database.json"
THRESH = 0.80
EXCLUSION_DAYS = 14
MAX_TRIES = 4000
TARGET_SAMPLES = 80
RNG = random.Random(2021)


def blocked_year_months() -> set[tuple[int, int]]:
    if not OUTBREAK_DB.exists():
        return set()
    out: set[tuple[int, int]] = set()
    for ev in json.loads(OUTBREAK_DB.read_text()):
        d0 = datetime.strptime(ev["date"], "%Y-%m-%d").date()
        for k in range(-EXCLUSION_DAYS, EXCLUSION_DAYS + 1):
            dd = d0 + timedelta(days=k)
            out.add((dd.year, dd.month))
    return out


def main() -> int:
    blocked = blocked_year_months()
    if not blocked:
        print("RESULT: WARN — no outbreak_database.json; skipped FAR sample")
        return 0
    scores: list[float] = []
    seen: set[tuple[int, int]] = set()
    tries = 0
    while len(scores) < TARGET_SAMPLES and tries < MAX_TRIES:
        tries += 1
        y = RNG.randint(1992, 2019)
        m = RNG.randint(1, 12)
        if (y, m) in blocked or (y, m) in seen:
            continue
        seen.add((y, m))
        try:
            s = compute_tess_score(datetime(y, m, 15))
        except Exception as e:
            print(f"RESULT: FAIL — compute_tess_score: {e}")
            return 1
        scores.append(s)
    if len(scores) < 20:
        print(f"RESULT: WARN — only {len(scores)} valid (y,m) samples after {tries} tries")
        return 0
    hi = sum(1 for s in scores if s > THRESH)
    rate = hi / len(scores)
    if rate <= 0.05:
        print(f"RESULT: PASS — P(TESS>{THRESH})={rate:.1%} on {len(scores)} non-outbreak months")
    elif rate <= 0.12:
        print(f"RESULT: WARN — P(TESS>{THRESH})={rate:.1%} (watch list)")
    else:
        print(f"RESULT: FAIL — P(TESS>{THRESH})={rate:.1%} too high on {len(scores)} months")
    return 0


if __name__ == "__main__":
    sys.exit(main())
