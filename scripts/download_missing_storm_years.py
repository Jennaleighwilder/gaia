#!/usr/bin/env python3
"""
Download missing Storm Events years (2008, 2010, 2013, 2014, 2015, 2016, 2017, 2025)
using correct filenames from NCEI index.
"""

from __future__ import annotations

import gzip
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "tests" / "fixtures" / "noaa_storm_events"
BASE_URL = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"

MISSING_YEARS = [2008, 2010, 2013, 2014, 2015, 2016, 2017, 2025]

# Correct filenames from index (different c-date than c20260316)
YEAR_TO_FILENAME = {
    2008: "StormEvents_details-ftp_v1.0_d2008_c20260318.csv.gz",
    2010: "StormEvents_details-ftp_v1.0_d2010_c20260320.csv.gz",
    2013: "StormEvents_details-ftp_v1.0_d2013_c20260320.csv.gz",
    2014: "StormEvents_details-ftp_v1.0_d2014_c20260318.csv.gz",
    2015: "StormEvents_details-ftp_v1.0_d2015_c20260318.csv.gz",
    2016: "StormEvents_details-ftp_v1.0_d2016_c20260318.csv.gz",
    2017: "StormEvents_details-ftp_v1.0_d2017_c20260320.csv.gz",
    2025: "StormEvents_details-ftp_v1.0_d2025_c20260318.csv.gz",
}


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for year in MISSING_YEARS:
        target = DATA_DIR / f"details_{year}.csv"
        if target.exists() and target.stat().st_size > 0:
            print(f"Skip {year} (exists, {target.stat().st_size} bytes)")
            continue
        fn = YEAR_TO_FILENAME.get(year)
        if not fn:
            print(f"No filename for {year}")
            continue
        url = BASE_URL + fn
        print(f"Downloading {year}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = gzip.decompress(r.read())
            target.write_bytes(data)
            print(f"  OK: {len(data)} bytes, {data.count(b'\n')} lines")
        except Exception as e:
            print(f"  Failed: {e}")


if __name__ == "__main__":
    main()
