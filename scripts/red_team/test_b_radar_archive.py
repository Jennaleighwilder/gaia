#!/usr/bin/env python3
"""
RED TEAM B: Radar tracker distribution on many F3+ events (not N=1).
Requires replay_day + Level-II archive wiring; otherwise honest WARN.
"""
from __future__ import annotations

import ast
import json
import random
import sys
from pathlib import Path

import scripts.red_team._paths  # noqa: F401

ROOT = scripts.red_team._paths.ROOT
FIXTURE = ROOT / "tests" / "fixtures" / "major_events_1950_present.json"
TRACKER = ROOT / "scripts" / "radar_storm_tracker.py"


def _f_scale(mag) -> int:
    if mag is None:
        return 0
    s = str(mag).upper().replace("EF", "F")
    if s.startswith("F"):
        s = s[1:]
    try:
        return int(s)
    except ValueError:
        return 0


def _has_replay_day() -> bool:
    if not TRACKER.exists():
        return False
    tree = ast.parse(TRACKER.read_text())
    return any(isinstance(n, ast.FunctionDef) and n.name == "replay_day" for n in ast.walk(tree))


def main() -> int:
    print("=== RED TEAM B: RADAR TRACKER ON EVENT SAMPLE (F3+) ===")
    print()
    if not FIXTURE.exists():
        print("RESULT: FAIL — tests/fixtures/major_events_1950_present.json missing")
        return 1

    with open(FIXTURE) as f:
        events = json.load(f)

    tornado_f3 = []
    for e in events:
        et = str(e.get("event_type", "")).lower()
        if "tornado" not in et:
            continue
        if _f_scale(e.get("magnitude")) < 3:
            continue
        d = e.get("date") or (e.get("event_datetime_utc") or "")[:10]
        if not d:
            continue
        tornado_f3.append({**e, "_date": d})

    print(f"F3+ tornado rows in fixture: {len(tornado_f3)}")

    rng = random.Random(42)
    sample_n = min(50, len(tornado_f3))
    sample = rng.sample(tornado_f3, sample_n) if tornado_f3 else []

    print(f"Sample size (seed=42): {sample_n}")
    if sample:
        print("  Example rows (date, state, mag):")
        for row in sample[:5]:
            print(f"    {row['_date']}  {row.get('state')}  {row.get('magnitude')}")
    print()

    if not _has_replay_day():
        print(
            "RESULT: WARN — scripts/radar_storm_tracker.py has no replay_day(); "
            "cannot compute lead-time distribution. Add batch replay + Level-II ingest."
        )
        print("  When implemented, rerun this script for detected/missed counts and lead quantiles.")
        return 0

    print("RESULT: WARN — replay_day stub present but corpus loop not wired in this test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
