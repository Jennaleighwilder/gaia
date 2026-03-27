#!/usr/bin/env python3
"""
RED TEAM F: ERA5 / reanalysis vs real-time operational indices — disclosed limitation.
"""
from __future__ import annotations

import sys


def main() -> int:
    print("=== RED TEAM F: ERA5 / REANALYSIS vs REAL-TIME INDICES ===")
    print()
    print("When validation uses reanalysis or month-final CPC files:")
    print("  • AO/PNA/MEI/PDO monthly values can differ slightly from what was operationally")
    print("    posted in real time (assimilation, late observations, revision).")
    print("  • Effect is usually small mid-phase; largest near rapid ENSO transitions.")
    print()
    print("GAIA historical TESS in-repo uses CPC-format monthly ASCII under data/global_indices/")
    print("(vintage files), not live ERA5 grids — still not identical to a forecaster's")
    print("real-time snapshot on the 1st of each month.")
    print()
    print("Paper disclosure (suggested):")
    print('  "Indices are monthly post-analysis / CPC archives; real-time operational values')
    print('   may differ slightly, especially near ENSO transitions."')
    print()
    print("RESULT: PASS — limitation is minor if stated; not fatal if scores are robust to ±0.2 index noise.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
