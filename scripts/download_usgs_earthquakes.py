#!/usr/bin/env python3
"""
Download USGS earthquake catalog 2000-2024, M3.0+.
Chunks by year to stay under 20k-event API limit.
"""

from __future__ import annotations

import csv
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "tests" / "fixtures" / "usgs_earthquakes"
BASE = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=csv&minmagnitude=3.0"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "earthquakes_2000_2025.csv"
    print("Downloading USGS earthquake catalog (M3.0+, 2000-2024, by year)...")
    all_rows = []
    header = None
    for year in range(2000, 2025):
        url = f"{BASE}&starttime={year}-01-01&endtime={year}-12-31"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                text = r.read().decode("utf-8", errors="replace")
            lines = text.strip().split("\n")
            if not lines:
                continue
            if header is None:
                header = lines[0]
            rows = list(csv.DictReader(lines))
            all_rows.extend(rows)
            print(f"  {year}: {len(rows)} events")
        except Exception as e:
            print(f"  {year}: {e}")
        time.sleep(0.5)
    if all_rows:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            w.writeheader()
            w.writerows(all_rows)
    m4_plus = sum(1 for r in all_rows if float(r.get("mag", 0) or 0) >= 4.0)
    print(f"Downloaded {len(all_rows)} earthquakes (M3.0+)")
    print(f"M4.0+: {m4_plus}")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
