#!/usr/bin/env python3
"""
Populate ERA5 caches from NetCDF files already on disk (no CDS API).

Typical use after manual CDS downloads:
  PYTHONPATH=. python3 scripts/process_local_era5_netcdf.py \\
    --daily-nc ~/Downloads/your_april_daily.nc --daily-year 2011 --daily-month 4 \\
    --monthly-nc ~/Downloads/your_monthly.nc --monthly-year 1979 --monthly-month 1

Daily AO for that month uses an **intramonth EOF** index when you pass --intramonth-ao
(insufficient months for CPC-style 1979–2000 EOF + 1981–2010 climatology).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.ingest.era5_daily_ao import (  # noqa: E402
    compute_intramonth_eof_daily_ao,
    import_netcdf_daily_to_cache,
    import_netcdf_monthly_to_cache,
    load_era5_daily_ao_archive,
    merge_daily_ao_into_archive,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Import local ERA5 NetCDF into GAIA cache")
    ap.add_argument("--daily-nc", type=Path, default=None, help="Daily statistics NetCDF")
    ap.add_argument("--daily-year", type=int, default=2011)
    ap.add_argument("--daily-month", type=int, default=4)
    ap.add_argument("--monthly-nc", type=Path, default=None, help="Monthly mean NetCDF")
    ap.add_argument("--monthly-year", type=int, default=1979)
    ap.add_argument("--monthly-month", type=int, default=1)
    ap.add_argument(
        "--intramonth-ao",
        action="store_true",
        help="Compute month-local EOF AO for imported daily month and merge into daily_ao_archive.json",
    )
    args = ap.parse_args()

    if args.monthly_nc and args.monthly_nc.exists():
        print(f"Import monthly -> hgt1000_monthly_{args.monthly_year}_{args.monthly_month:02d}.npy")
        import_netcdf_monthly_to_cache(args.monthly_nc, args.monthly_year, args.monthly_month)
    elif args.monthly_nc:
        print(f"Missing monthly file: {args.monthly_nc}", file=sys.stderr)

    hgts: dict | None = None
    if args.daily_nc and args.daily_nc.exists():
        print(
            f"Import daily -> hgt1000_daily_{args.daily_year}_{args.daily_month:02d}.json"
        )
        hgts = import_netcdf_daily_to_cache(args.daily_nc, args.daily_year, args.daily_month)
        print(f"  {len(hgts)} days")
    elif args.daily_nc:
        print(f"Missing daily file: {args.daily_nc}", file=sys.stderr)
        return 1

    if args.intramonth_ao and hgts is not None:
        ao = compute_intramonth_eof_daily_ao(hgts)
        merge_daily_ao_into_archive(ao)
        print(f"Intramonth EOF AO: merged {len(ao)} days into daily_ao_archive.json")
        print("\n=== Daily AO (intramonth EOF, this month only) ===")
        for d in sorted(ao):
            print(f"  {d}: {ao[d]:.3f}")

    arch = load_era5_daily_ao_archive()
    print(f"\nArchive total keys: {len(arch)}")

    apr = {d: arch[d] for d in sorted(arch) if d.startswith("2011-04")}
    jan = {d: arch[d] for d in sorted(arch) if d.startswith("2011-01")}
    if apr:
        print("\n=== April 2011 (in archive) ===")
        for d in sorted(apr):
            print(f"  {d}: {apr[d]:.3f}")
    if jan:
        print("\n=== January 2011 (in archive) ===")
        for d in sorted(jan):
            print(f"  {d}: {jan[d]:.3f}")
    elif args.intramonth_ao and args.daily_month == 4:
        print("\n(No January 2011 in archive — import a Jan 2011 daily NetCDF to compare.)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
