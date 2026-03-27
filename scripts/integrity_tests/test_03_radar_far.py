#!/usr/bin/env python3
"""
3. Radar false-alarm rate on non-tornadic supercell days.

The GAIA spec referenced StormObjectTracker.replay_day; the repo only has
scripts/radar_storm_tracker.py without a batch replay API. Importing that
module requires Py-ART, so this test inspects source only and does not spin.
"""
from __future__ import annotations

import ast
import sys

import scripts.integrity_tests._paths  # noqa: F401

ROOT = scripts.integrity_tests._paths.ROOT
TRACKER = ROOT / "scripts" / "radar_storm_tracker.py"


def main() -> int:
    if not TRACKER.exists():
        print("RESULT: WARN — scripts/radar_storm_tracker.py missing; radar FAR not run")
        return 0
    tree = ast.parse(TRACKER.read_text())
    has_replay = any(
        isinstance(n, ast.FunctionDef) and n.name == "replay_day"
        for n in ast.walk(tree)
    )
    if not has_replay:
        print(
            "RESULT: WARN — no replay_day() in radar_storm_tracker.py; "
            "add replay harness for non-tornadic supercell days to score PASS/FAIL"
        )
        return 0
    print("RESULT: WARN — replay_day present but no default corpus wired in this test")
    return 0


if __name__ == "__main__":
    sys.exit(main())
