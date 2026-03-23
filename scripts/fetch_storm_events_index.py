#!/usr/bin/env python3
"""
Fetch NCEI Storm Events index and resolve correct filenames per year.
Pattern: StormEvents_details-ftp_v1.0_dYYYY*.csv.gz
"""

from __future__ import annotations

import re
import urllib.request

INDEX_URL = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"


def fetch_index() -> dict[int, str]:
    """Return {year: filename} for latest details file per year."""
    req = urllib.request.Request(INDEX_URL, headers={"User-Agent": "GAIA/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", errors="replace")
    # Match StormEvents_details-ftp_v1.0_dYYYY_cYYYYMMDD.csv.gz
    pattern = re.compile(r"StormEvents_details-ftp_v1\.0_d(\d{4})_c(\d{8})\.csv\.gz")
    by_year = {}
    for m in pattern.finditer(html):
        year = int(m.group(1))
        cdate = int(m.group(2))
        full = m.group(0)
        # Keep latest c-date per year
        if year not in by_year or cdate > by_year[year][0]:
            by_year[year] = (cdate, full)
    return {y: fn for y, (_, fn) in sorted(by_year.items())}


if __name__ == "__main__":
    files = fetch_index()
    for y in sorted(files.keys()):
        print(f"{y}: {files[y]}")
