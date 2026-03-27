#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
import random

import netCDF4 as nc
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.path1_allphase_validation import get_enso_phase, load_oni_monthly, month_last_day
from scripts.path1_daily_window_validation import load_outbreaks

RUNS = ROOT / "runs"
REPORT_PATH = RUNS / "z500_fetch.log"
CACHE_DIR = ROOT / "data" / "cache" / "z500_neutral"
TMP_PARENT = ROOT / "tmp_cds"
DATASET = "reanalysis-era5-pressure-levels"
REQUEST_AREA = [50, -105, 25, -80]
GRID = [1.0, 1.0]
WINDOW_DAYS = 21
G = 9.80665


def build_neutral_centers(
    outbreaks: list[dict], oni_lookup: dict[tuple[int, int], float]
) -> tuple[list[datetime], list[datetime]]:
    neutral_outbreaks: list[datetime] = []
    controls: list[datetime] = []
    outbreak_years = {datetime.strptime(row["date"], "%Y-%m-%d").year for row in outbreaks}
    rng = random.Random(42)

    for outbreak in outbreaks:
        odate = datetime.strptime(outbreak["date"], "%Y-%m-%d")
        phase, _ = get_enso_phase(oni_lookup, odate.year, odate.month)
        if phase != "NEUTRAL":
            continue
        neutral_outbreaks.append(odate)

        control_years: list[int] = []
        for year in range(1990, 2026):
            if year in outbreak_years or abs(year - odate.year) < 2:
                continue
            control_phase, _ = get_enso_phase(oni_lookup, year, odate.month)
            if control_phase == "NEUTRAL":
                control_years.append(year)
        rng.shuffle(control_years)

        added = 0
        for control_year in control_years:
            cday = min(odate.day, month_last_day(control_year, odate.month))
            controls.append(datetime(control_year, odate.month, cday))
            added += 1
            if added >= 5:
                break

    return neutral_outbreaks, controls


def collect_dates_needed(
    outbreak_dates: list[datetime], control_dates: list[datetime]
) -> tuple[set[str], dict[tuple[int, int], set[int]]]:
    dates_needed: set[str] = set()
    months_needed: dict[tuple[int, int], set[int]] = defaultdict(set)
    for center_date in outbreak_dates + control_dates:
        for days_back in range(1, WINDOW_DAYS + 1):
            day = center_date - timedelta(days=days_back)
            ds = day.strftime("%Y-%m-%d")
            dates_needed.add(ds)
            months_needed[(day.year, day.month)].add(day.day)
    return dates_needed, months_needed


def load_month_cache(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    with path.open() as f:
        raw = json.load(f)
    out: dict[str, float] = {}
    for key, value in raw.items():
        try:
            out[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def extract_daily_means(netcdf_path: Path) -> dict[str, float]:
    ds = nc.Dataset(str(netcdf_path))
    try:
        z_var = ds.variables.get("z") or ds.variables.get("geopotential")
        if z_var is None:
            raise KeyError("missing geopotential variable")
        time_var = ds.variables.get("time") or ds.variables.get("valid_time")
        if time_var is None:
            raise KeyError("missing time/valid_time variable")
        calendar = getattr(time_var, "calendar", "standard")
        times = nc.num2date(time_var[:], time_var.units, calendar=calendar)
        out: dict[str, float] = {}
        for idx, stamp in enumerate(times):
            ds_key = f"{stamp.year:04d}-{stamp.month:02d}-{stamp.day:02d}"
            values = np.asarray(z_var[idx], dtype=np.float64).reshape(-1) / G
            out[ds_key] = float(np.nanmean(values))
        return out
    finally:
        ds.close()


def fetch_month(
    client,
    year: int,
    month: int,
    requested_days: list[str],
) -> dict[str, float]:
    with tempfile.TemporaryDirectory(dir=str(TMP_PARENT)) as tmpdir:
        outfile = Path(tmpdir) / f"z500_{year}_{month:02d}.nc"
        request = {
            "product_type": "reanalysis",
            "variable": ["geopotential"],
            "pressure_level": ["500"],
            "year": str(year),
            "month": [f"{month:02d}"],
            "day": requested_days,
            "time": ["12:00"],
            "area": REQUEST_AREA,
            "grid": GRID,
            "data_format": "netcdf",
            "download_format": "unarchived",
        }
        client.retrieve(DATASET, request, str(outfile))
        return extract_daily_means(outfile)


def main() -> int:
    RUNS.mkdir(exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    TMP_PARENT.mkdir(parents=True, exist_ok=True)
    buf = StringIO()

    def pr(line: str = "") -> None:
        print(line, flush=True)
        buf.write(line + "\n")
        REPORT_PATH.write_text(buf.getvalue())

    outbreaks = load_outbreaks()
    oni_lookup = load_oni_monthly()
    neutral_outbreaks, controls = build_neutral_centers(outbreaks, oni_lookup)
    dates_needed, months_needed = collect_dates_needed(neutral_outbreaks, controls)

    pr(f"Neutral outbreaks: {len(neutral_outbreaks)}")
    pr(f"Matched controls: {len(controls)}")
    pr(f"Total date windows: {len(dates_needed)}")
    pr(f"Unique months to fetch: {len(months_needed)}")
    pr(f"Estimated disk per month: ~2-3MB")
    pr(f"Estimated total: ~{len(months_needed) * 3}MB")

    to_fetch: list[tuple[int, int, list[str]]] = []
    cached_complete = 0
    cached_partial = 0
    for year, month in sorted(months_needed):
        cache_file = CACHE_DIR / f"z500_{year:04d}_{month:02d}.json"
        existing = load_month_cache(cache_file)
        needed_keys = {
            f"{year:04d}-{month:02d}-{day:02d}" for day in sorted(months_needed[(year, month)])
        }
        missing_keys = sorted(needed_keys - set(existing))
        if not missing_keys:
            cached_complete += 1
            continue
        if existing:
            cached_partial += 1
        to_fetch.append((year, month, [key[-2:] for key in missing_keys]))

    pr(f"Already cached complete: {cached_complete} months")
    pr(f"Cached partial: {cached_partial} months")
    pr(f"Need to fetch: {len(to_fetch)} months")

    if not to_fetch:
        result = subprocess.run(
            ["du", "-sh", str(CACHE_DIR)],
            capture_output=True,
            text=True,
            check=False,
        )
        pr("All months cached. Ready for validation.")
        pr(f"Cache files: {len(list(CACHE_DIR.glob('z500_*.json')))}")
        pr(f"Cache size: {result.stdout.strip()}")
        return 0

    import cdsapi

    client = cdsapi.Client()
    successes = 0
    failures: list[str] = []
    for year, month, missing_days in to_fetch:
        cache_file = CACHE_DIR / f"z500_{year:04d}_{month:02d}.json"
        existing = load_month_cache(cache_file)
        pr(f"Fetching Z500 {year}-{month:02d} ({len(missing_days)} days)...")
        try:
            fetched = fetch_month(client, year, month, missing_days)
            existing.update(fetched)
            with cache_file.open("w") as f:
                json.dump(dict(sorted(existing.items())), f, indent=2)
            successes += 1
            pr(f"  Saved {len(fetched)} fetched days, {len(existing)} total days in {cache_file.name}")
        except Exception as exc:
            failures.append(f"{year}-{month:02d}: {exc}")
            pr(f"  FAILED {year}-{month:02d}: {exc}")

    result = subprocess.run(
        ["du", "-sh", str(CACHE_DIR)],
        capture_output=True,
        text=True,
        check=False,
    )
    pr()
    pr("Z500 fetch complete.")
    pr(f"Successful month fetches: {successes}")
    pr(f"Failed month fetches: {len(failures)}")
    if failures:
        for line in failures[:20]:
            pr(f"  {line}")
    pr(f"Cache files: {len(list(CACHE_DIR.glob('z500_*.json')))}")
    pr(f"Cache size: {result.stdout.strip()}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
