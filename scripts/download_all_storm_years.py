#!/usr/bin/env python3
"""
Download ALL Storm Events years (1996-2025) using correct filenames from NCEI index.
"""

from __future__ import annotations

import gzip
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "tests" / "fixtures" / "noaa_storm_events"
BASE_URL = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"

def fetch_index():
    import re
    req = urllib.request.Request(BASE_URL, headers={"User-Agent": "GAIA/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", errors="replace")
    pat = re.compile(r"StormEvents_details-ftp_v1\.0_d(\d{4})_c(\d{8})\.csv\.gz")
    by_year = {}
    for m in pat.finditer(html):
        y, c = int(m.group(1)), int(m.group(2))
        if y not in by_year or c > by_year[y][0]:
            by_year[y] = (c, m.group(0))
    return {y: fn for y, (_, fn) in sorted(by_year.items())}


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    by_year = fetch_index()
    years = [y for y in sorted(by_year.keys()) if 1996 <= y <= 2025]
    for year in years:
        target = DATA_DIR / f"details_{year}.csv"
        if target.exists() and target.stat().st_size > 100_000:
            print(f"Skip {year} (exists)")
            continue
        fn = by_year[year]
        url = BASE_URL + fn
        print(f"Downloading {year}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = gzip.decompress(r.read())
            target.write_bytes(data)
            print(f"  OK: {len(data)} bytes")
        except Exception as e:
            print(f"  Failed: {e}")
        time.sleep(1)


if __name__ == "__main__":
    main()
