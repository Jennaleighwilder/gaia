#!/usr/bin/env python3
"""
Filter NOAA Storm Events for East TN counties (1996-2025).
Count qualifying events by type for backtest expansion.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "tests" / "fixtures" / "noaa_storm_events"

EAST_TN_COUNTIES = {
    "knox", "sevier", "blount", "greene", "hamblen",
    "hawkins", "washington", "grainger", "sullivan", "anderson",
}

# Event types for backtest (hail filtered to >= 1 inch in post-process)
EVENT_TYPES = {
    "tornado", "thunderstorm wind", "flash flood", "hail",
    "winter storm", "ice storm", "heavy snow", "wildfire",
    "landslide", "flood", "high wind", "extreme cold", "excessive heat",
}


def norm(s: str) -> str:
    return (s or "").strip().lower().replace(" county", "").replace(" co", "").strip()


def parse_magnitude_kt(row: dict, etype: str) -> float | None:
    """Parse magnitude to kt for thunderstorm_wind. Returns None if unparseable."""
    if "thunderstorm" not in etype and "wind" not in etype:
        return None
    mag = (row.get("MAGNITUDE") or "").strip().upper()
    if not mag:
        return None
    val = None
    for part in mag.replace("MPH", " ").replace("KT", " ").replace("KTS", " ").split():
        try:
            val = float(part)
            break
        except ValueError:
            pass
    if val is None:
        return None
    if "kt" in mag or "kts" in mag:
        return val
    return val / 1.15078  # mph -> kt


def is_hail_1inch(row: dict) -> bool:
    """Hail: only >= 1 inch."""
    mag = (row.get("MAGNITUDE") or "").strip()
    if not mag:
        return True  # unknown, include
    mag = mag.upper().replace("E", "").replace("F", "").replace("H", "").strip()
    try:
        val = float(mag.split()[0] if mag else 0)
        return val >= 1.0
    except (ValueError, IndexError):
        return True


TW_MIN_KT = 40  # Severe threshold 50 kt; < 40 kt = likely bad data


def main():
    print("Filtering East TN Storm Events (1996-2025)")
    print("=" * 60)

    total = 0
    by_year = {}
    by_type = {}
    tw_suspect = 0

    for year in range(1996, 2026):
        p = DATA_DIR / f"details_{year}.csv"
        if not p.exists():
            continue
        rows = []
        with open(p, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if norm(row.get("STATE", "")) != "tennessee":
                    continue
                county = norm(row.get("CZ_NAME", ""))
                if county not in EAST_TN_COUNTIES:
                    continue
                etype = norm(row.get("EVENT_TYPE", ""))
                if "hail" in etype and not is_hail_1inch(row):
                    continue
                if not any(t in etype for t in EVENT_TYPES):
                    continue
                # Exclude TW with implausible magnitude from primary count
                if "thunderstorm" in etype and "wind" in etype:
                    mag_kt = parse_magnitude_kt(row, etype)
                    if mag_kt is not None and mag_kt < TW_MIN_KT:
                        tw_suspect += 1
                        continue
                rows.append(row)
        by_year[year] = len(rows)
        total += len(rows)
        for r in rows:
            etype = norm(r.get("EVENT_TYPE", "other"))
            by_type[etype] = by_type.get(etype, 0) + 1

    print(f"\nThunderstorm wind events flagged DATA_QUALITY_SUSPECT (mag < {TW_MIN_KT} kt): {tw_suspect}")
    print(f"\nQualifying events in East TN (1996-2025): {total}")
    print("\nBy year:")
    for y in sorted(by_year.keys()):
        print(f"  {y}: {by_year[y]}")

    print("\nBy event type:")
    for t in sorted(by_type.keys(), key=lambda x: -by_type[x]):
        print(f"  {t}: {by_type[t]}")

    return total


if __name__ == "__main__":
    main()
