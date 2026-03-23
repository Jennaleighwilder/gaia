#!/usr/bin/env python3
"""
Parse NASA POWER CSV (YEAR, MO, DY or YEAR, DOY + value) and output date,pw_mm
for backtest dates. Pipe to manual_gps_pw_entry.py.

Usage:
  python scripts/ingest_nasa_power_to_gps_pw.py /path/to/POWER_*.csv | python scripts/manual_gps_pw_entry.py
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def get_dates_to_fetch() -> list[str]:
    """All severe event dates + quiet day dates."""
    dates = set()
    events = json.loads((ROOT / "tests" / "fixtures" / "east_tn_severe_events.json").read_text())
    for e in events:
        dates.add(e["date"])
    for p in (ROOT / "tests" / "fixtures" / "historical_observations").glob("quiet_*.json"):
        parts = p.stem.split("_")
        if len(parts) >= 2 and "-" in parts[1]:
            dates.add(parts[1])
    return sorted(dates)


def parse_nasa_power(path: Path) -> dict[str, float]:
    """
    Parse NASA POWER CSV. Skip header lines (start with - or letters).
    Data rows: YEAR, MO, DY, value OR YEAR, DOY, value.
    Returns {YYYY-MM-DD: value}.
    """
    out: dict[str, float] = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("-") or line[0].isalpha():
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 4:
                continue
            try:
                year = int(parts[0])
                val = float(parts[-1])
                # Check for YEAR, MO, DY format
                if len(parts) >= 4 and parts[1].isdigit() and parts[2].isdigit():
                    mo, dy = int(parts[1]), int(parts[2])
                    dt = datetime(year, mo, dy)
                    date_str = dt.strftime("%Y-%m-%d")
                    out[date_str] = val
                # YEAR, DOY format
                elif len(parts) >= 3 and parts[1].isdigit():
                    doy = int(parts[1])
                    dt = datetime(year, 1, 1)
                    from datetime import timedelta
                    dt = dt + timedelta(days=doy - 1)
                    date_str = dt.strftime("%Y-%m-%d")
                    out[date_str] = val
            except (ValueError, TypeError):
                continue
    return out


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Parse NASA POWER CSV for backtest dates")
    parser.add_argument("csv_path", type=Path, help="Path to NASA POWER CSV")
    parser.add_argument("--pw-cm", action="store_true", help="PW in cm (convert to mm)")
    args = parser.parse_args()

    path = args.csv_path
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    backtest_dates = set(get_dates_to_fetch())
    data = parse_nasa_power(path)
    scale = 10.0 if args.pw_cm else 1.0

    matched = 0
    for d in sorted(backtest_dates):
        if d in data:
            val = data[d] * scale
            print(f"{d},{val}")
            matched += 1

    print(f"# Matched {matched}/{len(backtest_dates)} backtest dates", file=sys.stderr)


if __name__ == "__main__":
    main()
