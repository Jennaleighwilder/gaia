#!/usr/bin/env python3
"""
Fetch ERA5 1000 hPa daily heights for La Niña validation years, compute daily AO,
write data/cache/era5_daily_ao/daily_ao_archive.json.

Prerequisites: ~/.cdsapirc; accept CDS licences (use each dataset’s Download tab →
Manage licences → Accept), including:
  https://cds.climate.copernicus.eu/datasets/reanalysis-era5-pressure-levels-monthly-means
  https://cds.climate.copernicus.eu/datasets/derived-era5-pressure-levels-daily-statistics
(Hourly `reanalysis-era5-pressure-levels` is optional; monthly-means is required for EOF.)

Order: EOF monthly (1979–2000) → climatology monthly (1981–2010) → daily heights
→ per-year AO (uses disk cache; first year pays EOF+climo cost once).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.ingest.era5_daily_ao import ERA5DailyAO, ERA5_DAILY_AO_ARCHIVE_PATH

# Key La Niña windows in Path 1 daily corpus (calendar years to pull).
LA_NINA_YEARS = (
    list(range(1998, 2002))
    + list(range(2007, 2009))
    + list(range(2010, 2013))
    + [2017, 2018]
    + list(range(2020, 2024))
)


def prefetch_climatology_monthly(ao: ERA5DailyAO) -> None:
    print("Prefetch monthly means for 1981–2010 climatology...")
    for year in range(1981, 2011):
        for month in range(1, 13):
            print(f"  climo {year}-{month:02d}...", end=" ", flush=True)
            ao.fetch_monthly_1000mb_heights(year, month)
            print("ok")


def prefetch_daily_heights(ao: ERA5DailyAO, years: list[int]) -> None:
    print(f"\nPrefetch daily 1000 hPa fields ({len(years)} years)...")
    for year in years:
        for month in range(1, 13):
            print(f"  {year}-{month:02d}...", end=" ", flush=True)
            try:
                d = ao.fetch_daily_1000mb_heights(year, month)
                print(f"{len(d)} days")
            except Exception as e:
                print(f"FAILED: {e}")


def print_month_2011(all_daily_ao: dict[str, float], label: str, prefix: str) -> None:
    print(f"\n=== {label} ===")
    for date in sorted(d for d in all_daily_ao if d.startswith(prefix)):
        print(f"  {date}: {all_daily_ao[date]:.3f}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch ERA5-based daily AO for La Niña years")
    ap.add_argument(
        "--only-year",
        type=int,
        default=None,
        help="Restrict prefetch + AO computation to this year (e.g. 2011 for April vs Jan check)",
    )
    args = ap.parse_args()

    years = [args.only_year] if args.only_year is not None else list(LA_NINA_YEARS)
    if args.only_year is not None:
        print(f"Single-year mode: {args.only_year}\n")

    ao = ERA5DailyAO()

    print("Computing AO loading pattern (monthly 1979–2000, one-time CDS cost)...")
    ao.compute_ao_loading_pattern()
    print()

    prefetch_climatology_monthly(ao)
    print()
    prefetch_daily_heights(ao, years)

    print("\nComputing daily AO index from cached heights...")
    all_daily_ao: dict[str, float] = {}
    for year in years:
        try:
            year_ao = ao.compute_daily_ao_for_period(year, year)
            n = len([k for k in year_ao if k.startswith(str(year))])
            print(f"  {year}: {n} days (series total {len(year_ao)})")
            all_daily_ao.update(year_ao)
        except Exception as e:
            print(f"  {year}: FAILED — {e}")

    ERA5_DAILY_AO_ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ERA5_DAILY_AO_ARCHIVE_PATH, "w", encoding="utf-8") as f:
        json.dump(all_daily_ao, f)
    print(f"\nSaved {len(all_daily_ao)} daily AO values -> {ERA5_DAILY_AO_ARCHIVE_PATH}")

    if any(y == 2011 for y in years):
        print_month_2011(all_daily_ao, "APRIL 2011 DAILY AO (ERA5)", "2011-04")
        print_month_2011(all_daily_ao, "JANUARY 2011 DAILY AO (ERA5)", "2011-01")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
