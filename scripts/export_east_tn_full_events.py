#!/usr/bin/env python3
"""
Export ALL East TN storm events (3,667) from NOAA Storm Events.
Output: east_tn_full_events.json for ASOS fetch + full backtest.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "tests" / "fixtures" / "noaa_storm_events"
OUT_PATH = ROOT / "tests" / "fixtures" / "east_tn_full_events.json"
SUSPECT_PATH = ROOT / "tests" / "fixtures" / "east_tn_suspect_tw_events.json"

# Severe thunderstorm wind threshold 50 kt (58 mph). Events < 40 kt are likely bad data.
TW_MIN_KT = 40

EAST_TN_COUNTIES = {
    "knox", "sevier", "blount", "greene", "hamblen",
    "hawkins", "washington", "grainger", "sullivan", "anderson",
}

COUNTY_TO_STATION = {
    "knox": "KTYS", "sevier": "KTYS", "blount": "KTYS", "anderson": "KTYS",
    "greene": "KGKT", "hamblen": "KGKT",
    "hawkins": "KTRI", "washington": "KTRI", "grainger": "KTRI", "sullivan": "KTRI",
}

EVENT_TYPES = {
    "tornado", "thunderstorm wind", "flash flood", "hail",
    "winter storm", "ice storm", "heavy snow", "wildfire",
    "landslide", "flood", "high wind", "extreme cold", "excessive heat",
    "marine high wind",
}

# Map NOAA event type to GAIA event_type
ETYPE_MAP = {
    "tornado": "tornado",
    "thunderstorm wind": "thunderstorm_wind",
    "flash flood": "flash_flood",
    "hail": "hail",
    "winter storm": "winter_storm",
    "ice storm": "ice_storm",
    "heavy snow": "heavy_snow",
    "wildfire": "wildfire",
    "landslide": "landslide",
    "flood": "flash_flood",  # treat as flash_flood for scoring
    "high wind": "thunderstorm_wind",
    "marine high wind": "thunderstorm_wind",
    "extreme cold": "winter_storm",
    "excessive heat": "thunderstorm_wind",  # thermal hazard
}


def norm(s: str) -> str:
    return (s or "").strip().lower().replace(" county", "").replace(" co", "").strip()


def is_hail_1inch(row: dict) -> bool:
    mag = (row.get("MAGNITUDE") or "").strip()
    if not mag:
        return True
    mag = mag.upper().replace("E", "").replace("F", "").replace("H", "").strip()
    try:
        val = float(mag.split()[0] if mag else 0)
        return val >= 1.0
    except (ValueError, IndexError):
        return True


def parse_begin_datetime_utc(row: dict) -> str | None:
    dt_str = (row.get("BEGIN_DATE_TIME") or "").strip()
    if not dt_str:
        return None
    m = re.match(r"(\d{1,2})-([A-Za-z]{3})-(\d{2,4})\s+(\d{1,2}):(\d{2}):(\d{2})", dt_str)
    if not m:
        return None
    day, mon_abbr, yr = int(m.group(1)), m.group(2), int(m.group(3))
    hr, mn, sec = int(m.group(4)), int(m.group(5)), int(m.group(6))
    year = 2000 + yr if yr < 100 else yr
    mon_map = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
               "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}
    month = mon_map.get(mon_abbr.upper(), 1)
    utc_offset = 4 if 3 <= month <= 10 else 5  # EDT vs EST
    dt_local = datetime(year, month, day, hr, mn, sec)
    dt_utc = dt_local + timedelta(hours=utc_offset)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_magnitude_kt(mag_str: str, etype: str) -> float | None:
    """Parse magnitude to kt. Returns None if unparseable. TW: 50 kt = severe."""
    if not mag_str or "thunderstorm" not in etype and "wind" not in etype:
        return None
    mag = (mag_str or "").strip().upper()
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
    if "mph" in mag or not any(u in mag for u in ("KT", "KTS")):
        return val / 1.15078  # mph -> kt
    return val


def magnitude_for_event(row: dict, etype: str) -> str:
    if "tornado" in etype:
        return (row.get("TOR_F_SCALE") or row.get("MAGNITUDE") or "").strip()
    if "thunderstorm" in etype or "wind" in etype:
        mag = (row.get("MAGNITUDE") or "").strip()
        if mag and "mph" not in mag.lower():
            return f"{mag} mph"
        return mag or ""
    if "hail" in etype:
        return (row.get("MAGNITUDE") or "").strip()
    return (row.get("MAGNITUDE") or "").strip()


def main():
    events = []
    suspect_tw = []
    for year in range(1996, 2026):
        p = DATA_DIR / f"details_{year}.csv"
        if not p.exists():
            continue
        with open(p, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if norm(row.get("STATE", "")) != "tennessee":
                    continue
                county = norm(row.get("CZ_NAME", ""))
                if county not in EAST_TN_COUNTIES:
                    continue
                etype_raw = norm(row.get("EVENT_TYPE", ""))
                if "hail" in etype_raw and not is_hail_1inch(row):
                    continue
                if not any(t in etype_raw for t in EVENT_TYPES):
                    continue
                event_id = (row.get("EVENT_ID") or "").strip()
                if not event_id:
                    continue
                begin_utc = parse_begin_datetime_utc(row)
                if not begin_utc:
                    continue
                event_type = ETYPE_MAP.get(etype_raw, etype_raw.replace(" ", "_"))
                station = COUNTY_TO_STATION.get(county, "KTYS")
                mag = magnitude_for_event(row, etype_raw)

                # Filter out TW events with implausible wind speeds (< 40 kt = bad data)
                if event_type == "thunderstorm_wind":
                    mag_kt = parse_magnitude_kt(mag, etype_raw)
                    if mag_kt is not None and mag_kt < TW_MIN_KT:
                        suspect_tw.append({
                            "event_id": event_id,
                            "date": begin_utc[:10],
                            "event_datetime_utc": begin_utc,
                            "county": county,
                            "station": station,
                            "event_type": event_type,
                            "magnitude": mag or "",
                            "magnitude_kt": round(mag_kt, 1),
                            "data_quality_suspect": "magnitude_implausible",
                        })
                        continue

                date_str = begin_utc[:10]
                events.append({
                    "event_id": event_id,
                    "date": date_str,
                    "event_datetime_utc": begin_utc,
                    "county": county,
                    "station": station,
                    "event_type": event_type,
                    "magnitude": mag or "",
                })
    events.sort(key=lambda e: (e["date"], e["event_id"]))
    suspect_tw.sort(key=lambda e: (e["date"], e["event_id"]))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(events, indent=2) + "\n")
    SUSPECT_PATH.write_text(json.dumps(suspect_tw, indent=2) + "\n")
    from collections import Counter
    by_type = Counter(e["event_type"] for e in events)
    print(f"Exported {len(events)} events to {OUT_PATH}")
    print(f"Thunderstorm wind events flagged as DATA_QUALITY_SUSPECT (magnitude < {TW_MIN_KT} kt): {len(suspect_tw)}")
    print(f"Suspect corpus saved to {SUSPECT_PATH}")
    for t, c in by_type.most_common(12):
        print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
