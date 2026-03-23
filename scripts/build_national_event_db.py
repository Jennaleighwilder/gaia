"""
Build the national severe weather event database.

Outputs:
  data/national_events.json
  data/national_events_major.json
  data/event_stats.json
"""

from __future__ import annotations

import csv
import glob
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path


SEVERE_TYPES = {
    "Tornado",
    "Thunderstorm Wind",
    "Hail",
    "Flash Flood",
    "Heavy Snow",
    "Ice Storm",
    "Winter Storm",
    "Blizzard",
    "High Wind",
    "Flood",
    "Strong Wind",
    "Heavy Rain",
    "Winter Weather",
    "Freezing Rain",
    "Excessive Heat",
    "Tropical Storm",
    "Hurricane",
    "Storm Surge/Tide",
}


def parse_damage(value: str) -> float:
    raw = (value or "").strip().upper()
    if not raw or raw in {"0", "0.00K"}:
        return 0.0
    try:
        if raw.endswith("K"):
            return float(raw[:-1]) * 1_000
        if raw.endswith("M"):
            return float(raw[:-1]) * 1_000_000
        if raw.endswith("B"):
            return float(raw[:-1]) * 1_000_000_000
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def is_major(row: dict) -> bool:
    injuries = int(row.get("INJURIES_DIRECT", 0) or 0)
    deaths = int(row.get("DEATHS_DIRECT", 0) or 0)
    if injuries > 0 or deaths > 0:
        return True

    if parse_damage(row.get("DAMAGE_PROPERTY", "")) >= 100_000:
        return True

    ef = (row.get("TOR_F_SCALE", "") or "").strip().upper()
    if ef in {"EF2", "EF3", "EF4", "EF5", "F2", "F3", "F4", "F5"}:
        return True

    event_type = (row.get("EVENT_TYPE", "") or "").strip()
    magnitude_type = (row.get("MAGNITUDE_TYPE", "") or "").strip().upper()
    try:
        magnitude = float(row.get("MAGNITUDE", "") or 0.0)
    except (TypeError, ValueError):
        magnitude = 0.0

    if magnitude_type in {"MG", "EG"} and magnitude >= 75:
        return True
    if event_type == "Hail" and magnitude >= 2.0:
        return True
    return False


def parse_date(row: dict) -> str:
    begin = (row.get("BEGIN_DATE_TIME", "") or "").strip()
    if begin:
        pieces = begin.split()
        if pieces:
            for fmt in ("%d-%b-%y", "%m/%d/%Y"):
                try:
                    return datetime.strptime(pieces[0], fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
    ym = (row.get("BEGIN_YEARMONTH", "") or "").strip()
    day = (row.get("BEGIN_DAY", "") or "").strip()
    if ym and day and len(ym) == 6:
        try:
            return f"{ym[:4]}-{ym[4:6]}-{int(day):02d}"
        except ValueError:
            return ""
    return ""


def parse_time_utc(row: dict) -> str:
    begin = (row.get("BEGIN_DATE_TIME", "") or "").strip()
    if begin and " " in begin:
        return begin.split()[1][:5]
    return ""


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    data_dir = root / "data" / "storm_events"
    files = sorted(glob.glob(str(data_dir / "details_*.csv")))
    if not files:
        print("No storm event files found in data/storm_events/")
        print("Run scripts/download_storm_events.sh first.")
        return

    all_events = []
    major_events = []
    eid = 0

    for filepath in files:
        print(f"Processing {os.path.basename(filepath)}...")
        with open(filepath, encoding="utf-8", errors="replace") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                event_type = (row.get("EVENT_TYPE", "") or "").strip()
                if event_type not in SEVERE_TYPES:
                    continue

                date = parse_date(row)
                if not date:
                    continue

                eid += 1
                event = {
                    "event_id": f"NAT_{eid:06d}",
                    "date": date,
                    "time_utc": parse_time_utc(row),
                    "state": (row.get("STATE", "") or "").strip(),
                    "county": (row.get("CZ_NAME", "") or "").strip(),
                    "event_type": event_type,
                    "magnitude": row.get("MAGNITUDE", ""),
                    "magnitude_type": row.get("MAGNITUDE_TYPE", ""),
                    "tor_f_scale": row.get("TOR_F_SCALE", ""),
                    "injuries": int(row.get("INJURIES_DIRECT", 0) or 0),
                    "deaths": int(row.get("DEATHS_DIRECT", 0) or 0),
                    "damage_property": row.get("DAMAGE_PROPERTY", ""),
                    "narrative": (row.get("EVENT_NARRATIVE", "") or "")[:300],
                    "begin_lat": row.get("BEGIN_LAT", ""),
                    "begin_lon": row.get("BEGIN_LON", ""),
                    "is_major": is_major(row),
                }
                all_events.append(event)
                if event["is_major"]:
                    major_events.append(event)

    all_events.sort(key=lambda item: item["date"])
    major_events.sort(key=lambda item: item["date"])

    output_dir = root / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "national_events.json").write_text(json.dumps(all_events, indent=2) + "\n")
    (output_dir / "national_events_major.json").write_text(json.dumps(major_events, indent=2) + "\n")

    type_counts = Counter(event["event_type"] for event in all_events)
    state_counts = Counter(event["state"] for event in all_events)
    year_counts = Counter(event["date"][:4] for event in all_events)
    major_type_counts = Counter(event["event_type"] for event in major_events)

    stats = {
        "total_events": len(all_events),
        "major_events": len(major_events),
        "by_type": dict(type_counts.most_common()),
        "major_by_type": dict(major_type_counts.most_common()),
        "by_state_top_20": dict(state_counts.most_common(20)),
        "by_year": dict(sorted(year_counts.items())),
        "total_injuries": sum(event["injuries"] for event in all_events),
        "total_deaths": sum(event["deaths"] for event in all_events),
        "total_tornadoes": type_counts.get("Tornado", 0),
        "major_tornadoes": major_type_counts.get("Tornado", 0),
    }
    (output_dir / "event_stats.json").write_text(json.dumps(stats, indent=2) + "\n")

    print()
    print("=" * 60)
    print("NATIONAL SEVERE WEATHER DATABASE BUILT")
    print("=" * 60)
    print(f"Total events:  {len(all_events):,}")
    print(f"Major events:  {len(major_events):,}")
    print()
    print("By type:")
    for event_type, count in type_counts.most_common(10):
        print(f"  {event_type:25s} {count:7,}  (major: {major_type_counts.get(event_type, 0):,})")
    print()
    print("By year:")
    for year, count in sorted(year_counts.items()):
        print(f"  {year}: {count:,}")
    print()
    print("Top 10 states:")
    for state, count in state_counts.most_common(10):
        print(f"  {state:20s} {count:,}")
    print()
    print(f"Total injuries: {stats['total_injuries']:,}")
    print(f"Total deaths:   {stats['total_deaths']:,}")
    print()
    print("Saved to:")
    print(f"  {output_dir / 'national_events.json'}")
    print(f"  {output_dir / 'national_events_major.json'}")
    print(f"  {output_dir / 'event_stats.json'}")


if __name__ == "__main__":
    main()
