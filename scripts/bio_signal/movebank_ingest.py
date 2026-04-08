#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "bio_signal"


def main() -> int:
    steps = [
        SCRIPT_DIR / "movebank_step1.py",
        SCRIPT_DIR / "movebank_step2.py",
        SCRIPT_DIR / "infrasound_check.py",
    ]
    for step in steps:
        print(f"Running {step.name}...")
        result = subprocess.run([sys.executable, str(step)], cwd=str(ROOT))
        if result.returncode != 0:
            return result.returncode
    print("Movebank / infrasound ingest complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
