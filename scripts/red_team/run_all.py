#!/usr/bin/env python3
"""
Run red-team tests A–F; append output to runs/red_team_report.txt

  PYTHONPATH=$PWD python scripts/red_team/run_all.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import scripts.red_team._paths  # noqa: F401

ROOT = scripts.red_team._paths.ROOT
RUNS = ROOT / "runs"
RUNS.mkdir(parents=True, exist_ok=True)
REPORT = RUNS / "red_team_report.txt"
HERE = Path(__file__).resolve().parent
TESTS = [
    HERE / "test_a_contingency.py",
    HERE / "test_b_radar_archive.py",
    HERE / "test_c_uvrk_acf.py",
    HERE / "test_d_nws_baseline.py",
    HERE / "test_e_debris_location.py",
    HERE / "test_f_era5_disclosure.py",
]
ENV = {**os.environ, "PYTHONPATH": str(ROOT)}


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    chunks: list[str] = [f"\n{'=' * 72}\nGAIA RED TEAM {stamp}\n{'=' * 72}\n"]
    worst = 0
    for script in TESTS:
        chunks.append(f"\n--- {script.name} ---\n")
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(ROOT),
            env=ENV,
            capture_output=True,
            text=True,
        )
        chunks.append(proc.stdout or "")
        if proc.stderr:
            chunks.append(proc.stderr)
        chunks.append(f"(exit {proc.returncode})\n")
        worst = max(worst, proc.returncode)

    summary = """
| Attack vector              | Test | Output expectation                          |
|----------------------------|------|---------------------------------------------|
| Biased outbreak corpus     | A    | Full 2×2, precision/recall/MCC at thresholds|
| N=1 radar case study       | B    | Distribution or WARN until replay exists   |
| Hurricane UVRK on tornadoes| C    | Monthly ACF + explicit parameter caveat     |
| 13 min NWS baseline        | D    | Dual baseline (all-tor vs major supercell) |
| Wrong debris / segment     | E    | Distance check; survey overlay TODO         |
| ERA5 / archive optimism    | F    | Disclosure text                             |

Run after TESS / index updates. Every FAIL/WARN is intentional signal.
"""
    chunks.append(summary)
    body = "".join(chunks)
    if REPORT.exists():
        REPORT.write_text(REPORT.read_text() + body)
    else:
        REPORT.write_text(body)
    print(body)
    print(f"\nAppended to {REPORT}")
    return min(worst, 1)


if __name__ == "__main__":
    sys.exit(main())
