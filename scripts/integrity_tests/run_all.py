#!/usr/bin/env python3
"""
Run all integrity tests and append output to runs/integrity_test_report.txt

Usage (from anywhere):
  python scripts/integrity_tests/run_all.py

Requires PYTHONPATH=repo root (this script sets it).
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RUNS = ROOT / "runs"
RUNS.mkdir(parents=True, exist_ok=True)
REPORT = RUNS / "integrity_test_report.txt"
HERE = Path(__file__).resolve().parent
TESTS = sorted(HERE.glob("test_*.py"))
ENV = {**os.environ, "PYTHONPATH": str(ROOT)}


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    blocks: list[str] = [f"\n{'=' * 72}\nGAIA integrity tests {stamp}\n{'=' * 72}\n"]
    exit_max = 0
    for script in TESTS:
        blocks.append(f"\n--- {script.name} ---\n")
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(ROOT),
            env=ENV,
            capture_output=True,
            text=True,
        )
        blocks.append(proc.stdout or "")
        if proc.stderr:
            blocks.append(proc.stderr)
        if proc.returncode != 0:
            blocks.append(f"(exit {proc.returncode})\n")
        exit_max = max(exit_max, proc.returncode)
    body = "".join(blocks)
    if REPORT.exists():
        REPORT.write_text(REPORT.read_text() + body)
    else:
        REPORT.write_text(body)
    print(f"Wrote appended report to {REPORT}")
    return min(exit_max, 1)  # 0 or 1 for shell


if __name__ == "__main__":
    sys.exit(main())
