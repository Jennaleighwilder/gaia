"""
Pull historical weather observations for GAIA backtesting.

Uses Iowa Environmental Mesonet ASOS data for hourly observations and
the NOAA Storm Events bulk database to verify quiet days.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.ingest.upper_air_client import UpperAirClient

IEM_STATIONS = {
    "TRI": {"name": "Tri-Cities Airport", "county": "sullivan"},
    "MOR": {"name": "Morristown Municipal", "county": "hamblen"},
    "TYS": {"name": "McGhee Tyson Airport", "county": "blount"},
    "GKT": {"name": "Gatlinburg-Pigeon Forge", "county": "sevier"},
}

COUNTY_TO_STATION = {
    "hawkins": "TRI",
    "sullivan": "TRI",
    "washington": "TRI",
    "greene": "TRI",
    "hamblen": "MOR",
    "grainger": "MOR",
    "sevier": "GKT",
    "blount": "TYS",
    "knox": "TYS",
}

TARGET_COUNTIES = {
    "HAWKINS",
    "SULLIVAN",
    "WASHINGTON",
    "GREENE",
    "HAMBLEN",
    "GRAINGER",
    "SEVIER",
    "BLOUNT",
    "KNOX",
}

SEVERE_TYPES = {
    "Tornado",
    "Thunderstorm Wind",
    "Flash Flood",
    "Hail",
    "Ice Storm",
    "Heavy Snow",
    "Winter Storm",
}

IEM_BASE = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
NOAA_BASE = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
NOAA_FILES = [
    "StormEvents_details-ftp_v1.0_d2020_c20260316.csv.gz",
    "StormEvents_details-ftp_v1.0_d2021_c20260316.csv.gz",
    "StormEvents_details-ftp_v1.0_d2022_c20260316.csv.gz",
    "StormEvents_details-ftp_v1.0_d2023_c20260316.csv.gz",
    "StormEvents_details-ftp_v1.0_d2024_c20260316.csv.gz",
    "StormEvents_details-ftp_v1.0_d2025_c20260318.csv.gz",
]
SOUNDING_STATIONS = ["RNK", "BNA", "GSO"]


def _float(val):
    if val in (None, "", "null", "M"):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _kts_to_mph(val):
    parsed = _float(val)
    return round(parsed * 1.15078, 1) if parsed is not None else None


def _utc(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_events(path: Path) -> list[dict]:
    return json.loads(path.read_text())


def load_noaa_severe_dates() -> set[str]:
    severe_dates: set[str] = set()
    for filename in NOAA_FILES:
        raw = urllib.request.urlopen(NOAA_BASE + filename, timeout=120).read()
        text = gzip.decompress(raw).decode("utf-8", errors="replace")
        for row in csv.DictReader(io.StringIO(text)):
            if row.get("STATE") != "TENNESSEE":
                continue
            if row.get("CZ_NAME", "").strip().upper() not in TARGET_COUNTIES:
                continue
            if row.get("EVENT_TYPE") not in SEVERE_TYPES:
                continue
            begin = row.get("BEGIN_DATE_TIME")
            if not begin:
                continue
            dt = datetime.strptime(begin, "%d-%b-%y %H:%M:%S")
            severe_dates.add(dt.strftime("%Y-%m-%d"))
    return severe_dates


def select_quiet_date(event_date: str, severe_dates: set[str]) -> str | None:
    event_dt = datetime.strptime(event_date, "%Y-%m-%d")
    candidates = [5, 7, 10, -5, -7, -10, 14, -14]
    for offset in candidates:
        candidate = event_dt + timedelta(days=offset)
        if candidate.month != event_dt.month:
            continue
        day = candidate.strftime("%Y-%m-%d")
        if day not in severe_dates:
            return day
    for day_num in range(1, 32):
        try:
            candidate = event_dt.replace(day=day_num)
        except ValueError:
            continue
        day = candidate.strftime("%Y-%m-%d")
        if day not in severe_dates:
            return day
    return None


def pull_iem_observations(station: str, start_dt: datetime, end_dt: datetime) -> list[dict]:
    start_dt = start_dt.astimezone(timezone.utc)
    end_dt = end_dt.astimezone(timezone.utc)
    query_end = end_dt + timedelta(days=1)
    url = (
        f"{IEM_BASE}?"
        f"station={station}&data=all&"
        f"year1={start_dt.year}&month1={start_dt.month}&day1={start_dt.day}&"
        f"year2={query_end.year}&month2={query_end.month}&day2={query_end.day}&"
        f"tz=UTC&format=onlycomma&latlon=yes&elev=yes&missing=null&trace=0.0001&report_type=3"
    )

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "(GAIA Weather Engine, theforgottencode780@gmail.com)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8", errors="replace")

    observations = []
    for row in csv.DictReader(io.StringIO(text)):
        ts = row.get("valid")
        if not ts:
            continue
        obs_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        if obs_dt < start_dt or obs_dt > end_dt:
            continue
        observations.append(
            {
                "timestamp": obs_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "station_id": f"K{station}",
                "temperature_f": _float(row.get("tmpf")),
                "dewpoint_f": _float(row.get("dwpf")),
                "pressure_mb": _float(row.get("mslp")),
                "wind_speed_mph": _kts_to_mph(row.get("sknt")),
                "wind_direction_deg": _float(row.get("drct")),
                "wind_gust_mph": _kts_to_mph(row.get("gust")),
                "visibility_mi": _float(row.get("vsby")),
                "humidity_pct": _float(row.get("relh")),
                "sky_condition": row.get("skyc1", ""),
                "precip_1h_in": _float(row.get("p01i")),
                "metar": row.get("metar", ""),
            }
        )
    return observations


def sounding_candidates(event_dt: datetime) -> list[datetime]:
    event_dt = event_dt.astimezone(timezone.utc)
    same_day_00 = event_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    same_day_12 = event_dt.replace(hour=12, minute=0, second=0, microsecond=0)
    prev_day_12 = same_day_12 - timedelta(days=1)
    prev_day_00 = same_day_00 - timedelta(days=1)
    if event_dt.hour >= 18:
        return [same_day_12, same_day_00, prev_day_12]
    if event_dt.hour >= 6:
        return [same_day_00, prev_day_12, prev_day_00]
    return [same_day_00, prev_day_12, prev_day_00]


def pull_upper_air_for_datetime(client: UpperAirClient, event_dt: datetime) -> dict | None:
    for station in SOUNDING_STATIONS:
        for sounding_time in sounding_candidates(event_dt):
            try:
                sounding = client.get_real_sounding(station, sounding_time, publish=False)
                parameters = sounding.get("parameters") or {}
                if parameters:
                    return {
                        **parameters,
                        "sounding_source": f"{station}_{sounding_time.hour:02d}Z",
                        "sounding_valid_time_utc": sounding.get("valid_time_utc"),
                        "sounding_station": station,
                    }
            except Exception:
                continue
    return None


def main() -> None:
    root = ROOT
    events_path = root / "tests/fixtures/east_tn_severe_events.json"
    output_dir = root / "tests/fixtures/historical_observations"
    output_dir.mkdir(parents=True, exist_ok=True)
    upper_air_client = UpperAirClient()

    if not events_path.exists():
        print(f"Event database not found at {events_path}")
        return

    events = load_events(events_path)
    severe_dates = load_noaa_severe_dates()
    print(f"Loaded {len(events)} events and {len(severe_dates)} severe dates from NOAA.")
    print()

    for event in events:
        event_id = event["event_id"]
        station = COUNTY_TO_STATION.get(event["county"], "TRI")
        event_dt = _utc(event["event_datetime_utc"])
        start_dt = event_dt - timedelta(hours=12)
        output_path = output_dir / f"event_{event_id}.json"

        print(f"[{event_id}] {event['date']} {event['event_type']} in {event['county']} -> {station}")
        observations = pull_iem_observations(station, start_dt, event_dt)
        upper_air = pull_upper_air_for_datetime(upper_air_client, event_dt)
        payload = {
            "event_id": event_id,
            "event_date": event["date"],
            "event_time_utc": event["time_utc"],
            "event_datetime_utc": event["event_datetime_utc"],
            "station": f"K{station}",
            "county": event["county"],
            "event_type": event["event_type"],
            "observation_count": len(observations),
            "observations": observations,
            "upper_air": upper_air,
        }
        output_path.write_text(json.dumps(payload, indent=2) + "\n")
        upper_air_note = upper_air.get("sounding_source") if upper_air else "none"
        print(f"         -> {len(observations)} observations saved, upper air: {upper_air_note}")
        time.sleep(1)

    print()
    print("Pulling quiet day observations...")
    for event in events:
        station = COUNTY_TO_STATION.get(event["county"], "TRI")
        quiet_date = select_quiet_date(event["date"], severe_dates)
        if quiet_date is None:
            print(f"[quiet] no quiet date found for {event['event_id']}")
            continue

        quiet_dt = _utc(f"{quiet_date}T{event['time_utc']}:00Z")
        start_dt = quiet_dt - timedelta(hours=12)
        quiet_id = f"{quiet_date}_{station}"
        output_path = output_dir / f"quiet_{quiet_id}.json"

        print(f"[quiet] {quiet_date} @ {station}")
        observations = pull_iem_observations(station, start_dt, quiet_dt)
        upper_air = pull_upper_air_for_datetime(upper_air_client, quiet_dt)
        payload = {
            "quiet_id": quiet_id,
            "date": quiet_date,
            "event_time_utc": event["time_utc"],
            "station": f"K{station}",
            "county": event["county"],
            "observation_count": len(observations),
            "note": "Selected as a same-month quiet comparison with no NOAA severe reports in target counties.",
            "observations": observations,
            "upper_air": upper_air,
        }
        output_path.write_text(json.dumps(payload, indent=2) + "\n")
        upper_air_note = upper_air.get("sounding_source") if upper_air else "none"
        print(f"         -> {len(observations)} observations saved, upper air: {upper_air_note}")
        time.sleep(1)

    print()
    print("Historical data pull complete.")
    print(f"Event observations: {output_dir}/event_*.json")
    print(f"Quiet observations: {output_dir}/quiet_*.json")


if __name__ == "__main__":
    main()
