#!/usr/bin/env python3
"""
Fetch SMAP soil moisture from NASA Earthdata.
Requires: Register at https://urs.earthdata.nasa.gov/
Add applications: NASA GESDISC DATA ARCHIVE, NSIDC ECS
Set env: EARTHDATA_USER, EARTHDATA_PASS (or use .netrc)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "soil"
# SMAP SPL3SMP 9km: https://n5eil01u.ecs.nsidc.org/SMAP/SPL3SMP.008/


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=36.3)
    ap.add_argument("--lon", type=float, default=-83.9)
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--end", default="2025-12-31")
    args = ap.parse_args()
    user = os.environ.get("EARTHDATA_USER")
    passwd = os.environ.get("EARTHDATA_PASS")
    if not user or not passwd:
        print("Set EARTHDATA_USER and EARTHDATA_PASS (from urs.earthdata.nasa.gov)")
        print("Or add to ~/.netrc: machine urs.earthdata.nasa.gov login USER password PASS")
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # SMAP fetch requires authentication; placeholder for full implementation
    print(f"SMAP soil moisture fetch: ({args.lat},{args.lon}) {args.start} to {args.end}")
    print("Full implementation: use earthaccess or requests with netrc")
    print("  pip install earthaccess")
    print("  earthaccess login")
    return 0


if __name__ == "__main__":
    sys.exit(main())
