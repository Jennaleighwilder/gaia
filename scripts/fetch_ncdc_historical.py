#!/usr/bin/env python3
"""
Fetch NCDC / NCEI ISD-lite (global hourly) style data for historical stations.

Primary catalog: https://www.ncei.noaa.gov/data/global-hourly/

This script documents the workflow and implements a small helper to build
request URLs. Full bulk download is left to the operator (many TB).

Usage:
  .venv/bin/python scripts/fetch_ncdc_historical.py --station 72530094846 --year 1974 --month 4
"""

from __future__ import annotations

import argparse
import urllib.parse
import urllib.request

# ISD-lite access pattern (station-year files). Station IDs are typically
# WBAN-style 11-digit where available; see inventory CSVs on the NCEI site.
ISD_LITE_BASE = "https://www.ncei.noaa.gov/data/global-hourly/access"


def isd_lite_file_url(station_id: str, year: int) -> str:
    """Return URL for one station-year CSV (if published under access/)."""
    sid = urllib.parse.quote(station_id.strip(), safe="")
    return f"{ISD_LITE_BASE}/{year}/{sid}.csv"


def fetch_to_path(url: str, out_path: str, timeout: int = 120) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
    except Exception as e:
        print(f"Fetch failed: {e}")
        return False
    with open(out_path, "wb") as f:
        f.write(data)
    print(f"Wrote {len(data)} bytes -> {out_path}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Sample fetch from NCEI global-hourly access tree.")
    ap.add_argument("--station", required=True, help="Station ID (e.g. WBAN from inventory)")
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--output", default="ncdc_hourly_sample.csv")
    args = ap.parse_args()
    url = isd_lite_file_url(args.station, args.year)
    print(url)
    return 0 if fetch_to_path(url, args.output) else 1


if __name__ == "__main__":
    raise SystemExit(main())
