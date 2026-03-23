#!/usr/bin/env python3
"""
Test GOES TPW extraction using a pre-downloaded fixture.
Run this when S3 is unreachable (proxy/etc) to verify parse logic.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "goes16_tpw_sample.nc"


def main():
    sys.path.insert(0, str(ROOT))
    from runtime.data.goes_tpw import _extract_tpw_for_region

    if not FIXTURE.exists():
        print("No fixture at", FIXTURE)
        print("To create: run fetch_goes_tpw_east_tn.py once when S3 works, then:")
        print("  cp /tmp/goes_tpw_sample.nc tests/fixtures/goes16_tpw_sample.nc")
        return 1

    raw = FIXTURE.read_bytes()
    mm, inches = _extract_tpw_for_region(raw)
    print("From fixture", FIXTURE.name)
    print("  TPW (mm):  ", mm)
    print("  TPW (in):  ", inches)
    if mm is not None:
        print("  SUCCESS: GOES-16 TPW extraction works.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
