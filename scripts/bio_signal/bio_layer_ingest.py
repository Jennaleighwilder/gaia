#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "bio_signal"


def main() -> int:
    scripts = [
        SCRIPT_DIR / "bio_birdcast.py",
        SCRIPT_DIR / "bio_bioscatter.py",
        SCRIPT_DIR / "bio_insects.py",
    ]
    for script in scripts:
        print(f"Running {script.name}...")
        result = subprocess.run([sys.executable, str(script)], cwd=str(ROOT))
        if result.returncode != 0:
            return result.returncode
    print("Bio layer ingest complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
