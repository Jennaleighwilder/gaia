#!/usr/bin/env python3
"""Build major-events JSON from decompressed NCEI StormEvents_details*.csv files."""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _tor_scale_ge_3(row: dict) -> bool:
    s = (row.get("TOR_F_SCALE") or "").strip().upper()
    if not s:
        return False
    m = re.search(r"(?:EF|F)?(\d)", s)
    if not m:
        return False
    return int(m.group(1)) >= 3


def _deaths(row: dict) -> int:
    try:
        return int(row.get("DEATHS_DIRECT") or 0)
    except (TypeError, ValueError):
        return 0


def _injuries(row: dict) -> int:
    try:
        return int(row.get("INJURIES_DIRECT") or 0)
    except (TypeError, ValueError):
        return 0


def _date_prefix(row: dict) -> str:
    raw = (row.get("BEGIN_DATE_TIME") or "").strip()
    if len(raw) >= 10 and raw[4] == "-":
        return raw[:10]
    from datetime import datetime

    year_hint = _year(row)
    for fmt in ("%d-%b-%y %H:%M:%S", "%d-%b-%Y %H:%M:%S", "%d-%b-%y", "%d-%b-%Y"):
        try:
            dt = datetime.strptime(raw[:26].strip(), fmt)
            if year_hint and dt.year != year_hint and abs(dt.year - year_hint) >= 50:
                dt = dt.replace(year=year_hint)
            elif dt.year > 2035 and year_hint and year_hint < 2000:
                dt = dt.replace(year=year_hint)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Fallback: BEGIN_YEARMONTH (YYYYMM) + BEGIN_DAY
    try:
        ym = int(row.get("BEGIN_YEARMONTH") or 0)
        day = int(row.get("BEGIN_DAY") or 0)
        if ym >= 180001 and day:
            y, m = divmod(ym, 100)
            if m > 12:
                y, m = ym // 100, ym % 100
            return f"{y:04d}-{m:02d}-{day:02d}"
    except (TypeError, ValueError):
        pass
    return ""


def _year(row: dict) -> int:
    try:
        return int(row.get("YEAR") or 0)
    except (TypeError, ValueError):
        return 0


def qualifies_major(row: dict) -> bool:
    et = (row.get("EVENT_TYPE") or "").lower().strip()
    d = _deaths(row)

    if et == "tornado":
        return _tor_scale_ge_3(row)
    if "flash flood" in et:
        return d > 0
    if et == "flood" and d > 0:
        return True
    if "hurricane" in et or et == "tropical storm":
        return True
    if et == "blizzard":
        return True
    if "ice storm" in et or et == "ice storm":
        return d > 0
    if "wildfire" in et or et == "wildfire":
        return d > 0
    if "extreme cold" in et or et == "extreme cold":
        return d > 2
    if "excessive heat" in et:
        return d > 2
    if "tsunami" in et:
        return True
    if et == "avalanche":
        return True
    if "debris flow" in et:
        return True
    if "landslide" in et:
        return True
    return False


def _year_from_csv_name(path: Path) -> int | None:
    m = re.search(r"_d(\d{4})_", path.name)
    return int(m.group(1)) if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--storm-dir",
        type=Path,
        default=ROOT / "tests/fixtures/noaa_storm_events",
        help="Directory with StormEvents_details*.csv",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=ROOT / "tests/fixtures/major_events_1950_present.json",
    )
    ap.add_argument(
        "--years",
        type=str,
        default=None,
        help="Inclusive range e.g. 1996-2025 (filters CSV files by year in filename)",
    )
    args = ap.parse_args()

    y_min = y_max = None
    if args.years:
        parts = args.years.replace(" ", "").split("-", 1)
        if len(parts) == 2:
            y_min, y_max = int(parts[0]), int(parts[1])

    major_events: list[dict] = []
    csv_files = sorted(args.storm_dir.glob("StormEvents_details*.csv"))
    if y_min is not None:
        csv_files = [p for p in csv_files if (fy := _year_from_csv_name(p)) is not None and y_min <= fy <= y_max]
    if not csv_files:
        print(f"No CSV under {args.storm_dir}; run scripts/download_noaa_storm_events.py first.")
        return 1

    for csv_file in csv_files:
        if csv_file.stat().st_size == 0:
            print(f"Skip empty: {csv_file.name}")
            continue
        try:
            with open(csv_file, encoding="latin-1", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        if not qualifies_major(row):
                            continue
                        lat = float(row.get("BEGIN_LAT") or 0)
                        lon = float(row.get("BEGIN_LON") or 0)
                        eid = (row.get("EVENT_ID") or "").strip()
                        st = (row.get("STATE") or "").strip()
                        date_s = _date_prefix(row)
                        major_events.append(
                            {
                                "event_id": f"noaa_{eid}_{st}" if eid else f"noaa_row_{len(major_events)}",
                                "event_type": (row.get("EVENT_TYPE") or "").strip(),
                                "state": st,
                                "county": (row.get("CZ_NAME") or "").strip(),
                                "date": date_s,
                                "event_datetime_utc": f"{date_s}T18:00:00Z" if len(date_s) == 10 else "",
                                "year": _year(row),
                                "deaths": _deaths(row),
                                "injuries": _injuries(row),
                                "magnitude": (row.get("TOR_F_SCALE") or row.get("MAGNITUDE") or "").strip(),
                                "lat": lat,
                                "lon": lon,
                                "narrative": ((row.get("EVENT_NARRATIVE") or "")[:200]),
                                "source_file": csv_file.name,
                                "noaa_event_id": eid,
                            }
                        )
                    except Exception:
                        continue
        except Exception as e:
            print(f"Error {csv_file.name}: {e}")

    by_type = collections.Counter(e["event_type"] for e in major_events)
    by_decade = collections.Counter()
    for e in major_events:
        y = int(e.get("year") or 0)
        if y:
            by_decade[f"{y // 10 * 10}s"] += 1

    print(f"Total major events (filtered): {len(major_events)}")
    print("By type (top 15):")
    for k, v in by_type.most_common(15):
        print(f"  {k}: {v}")
    print("By decade:")
    for k, v in sorted(by_decade.items()):
        print(f"  {k}: {v}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(major_events, indent=2))
    print(f"Saved -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
