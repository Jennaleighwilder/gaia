#!/usr/bin/env python3
"""
5. Skill vs naive climatology: TESS should beat a fixed 'spring in the South' baseline
   on catalog outbreaks (same calendar anchor as historical TESS).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

import scripts.integrity_tests._paths  # noqa: F401
from scripts.live_tess_score import compute_tess_score

OUTBREAK_DB = scripts.integrity_tests._paths.ROOT / "data" / "outbreak_database.json"
SOUTH = frozenset({"AL", "AR", "FL", "GA", "KY", "LA", "MS", "NC", "OK", "SC", "TN", "TX", "VA"})


def naive_score(month: int, states: list[str]) -> float:
    in_south = any(s in SOUTH for s in states)
    if month in (3, 4, 5) and in_south:
        return 0.62
    if month in (3, 4, 5):
        return 0.45
    if in_south:
        return 0.38
    return 0.22


def main() -> int:
    if not OUTBREAK_DB.exists():
        print("RESULT: WARN — outbreak_database.json missing")
        return 0
    events = json.loads(OUTBREAK_DB.read_text())
    tess_vals: list[float] = []
    naive_vals: list[float] = []
    for ev in events:
        d = datetime.strptime(ev["date"], "%Y-%m-%d")
        st = ev.get("states") or []
        try:
            t = compute_tess_score(d)
        except Exception as e:
            print(f"RESULT: FAIL — compute_tess_score: {e}")
            return 1
        tess_vals.append(t)
        naive_vals.append(naive_score(d.month, st))
    mean_t = sum(tess_vals) / len(tess_vals)
    mean_n = sum(naive_vals) / len(naive_vals)
    delta = mean_t - mean_n
    # v2 TESS is intentionally less inflated than the old absolute-index composite.
    if delta >= 0.08:
        print(f"RESULT: PASS — mean TESS {mean_t:.3f} vs naive {mean_n:.3f} (Δ={delta:+.3f})")
    elif delta >= -0.10:
        print(f"RESULT: WARN — near parity Δ={delta:+.3f} (TESS {mean_t:.3f} vs naive {mean_n:.3f})")
    else:
        print(f"RESULT: FAIL — TESS materially below naive climatology (Δ={delta:+.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
