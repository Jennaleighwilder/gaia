"""
Pull national historical observations for the sampled backtest events.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import math
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
IEM_BASE = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
AVIATION_STATIONS_URL = "https://aviationweather.gov/data/cache/stations.cache.json.gz"


def _float(value):
    if value in (None, "", "null", "M"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _kts_to_mph(value):
    parsed = _float(value)
    return round(parsed * 1.15078, 1) if parsed is not None else None


def _dt(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius_miles * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_station_catalog() -> list[dict]:
    cache_path = ROOT / "data/stations_cache.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    raw = urllib.request.urlopen(AVIATION_STATIONS_URL, timeout=30).read()
    stations = json.loads(gzip.decompress(raw))
    filtered = [
        {
            "icaoId": station.get("icaoId"),
            "lat": station.get("lat"),
            "lon": station.get("lon"),
            "state": station.get("state"),
            "country": station.get("country"),
            "siteType": station.get("siteType") or [],
        }
        for station in stations
        if station.get("country") == "US" and station.get("icaoId") and "METAR" in (station.get("siteType") or [])
    ]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(filtered, indent=2) + "\n")
    return filtered


def candidate_stations(lat: float, lon: float, stations: list[dict], limit: int = 20) -> list[dict]:
    ranked = []
    for station in stations:
        station_lat = station.get("lat")
        station_lon = station.get("lon")
        if station_lat is None or station_lon is None:
            continue
        distance = haversine_miles(lat, lon, float(station_lat), float(station_lon))
        ranked.append((distance, station))
    ranked.sort(key=lambda item: item[0])
    return [{**station, "distance_miles": round(distance, 2)} for distance, station in ranked[:limit]]


def pull_iem_observations(station: str, start_dt: datetime, end_dt: datetime) -> list[dict]:
    query_end = end_dt + timedelta(days=1)
    url = (
        f"{IEM_BASE}?"
        f"station={station}&data=all&"
        f"year1={start_dt.year}&month1={start_dt.month}&day1={start_dt.day}&"
        f"year2={query_end.year}&month2={query_end.month}&day2={query_end.day}&"
        f"tz=UTC&format=onlycomma&latlon=yes&elev=yes&missing=null&trace=0.0001&report_type=3"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "(GAIA Weather Engine, theforgottencode780@gmail.com)"})
    with urllib.request.urlopen(req, timeout=45) as resp:
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
                "station_id": row.get("station") or station,
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


def build_daily_summaries(observations: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for observation in observations:
        grouped[observation["timestamp"][:10]].append(observation)

    summaries = []
    for day in sorted(grouped.keys()):
        chunk = grouped[day]
        pressures = [obs["pressure_mb"] for obs in chunk if obs.get("pressure_mb") is not None]
        temps = [obs["temperature_f"] for obs in chunk if obs.get("temperature_f") is not None]
        wind_dirs = [obs["wind_direction_deg"] for obs in chunk if obs.get("wind_direction_deg") is not None]
        dominant_wind = wind_dirs[0] if wind_dirs else None
        summaries.append(
            {
                "date": day,
                "mean_pressure": round(sum(pressures) / len(pressures), 4) if pressures else None,
                "mean_temp": round(sum(temps) / len(temps), 4) if temps else None,
                "dominant_wind_dir": dominant_wind,
                "precip_total": round(sum((obs.get("precip_1h_in") or 0.0) for obs in chunk), 4),
                "temp_range": round(max(temps) - min(temps), 4) if len(temps) >= 2 else None,
            }
        )
    return summaries


def pick_quiet_date(event: dict, state_dates: dict[str, set[str]], used_quiet_ids: set[str]) -> str | None:
    state = event["state"]
    event_dt = datetime.strptime(event["date"], "%Y-%m-%d")
    candidates = [5, 7, 10, -5, -7, -10, 14, -14, 21, -21]
    for offset in candidates:
        candidate = event_dt + timedelta(days=offset)
        if candidate.month != event_dt.month:
            continue
        date_str = candidate.strftime("%Y-%m-%d")
        if date_str not in state_dates[state]:
            quiet_id = f"{date_str}_{event['event_id']}"
            if quiet_id not in used_quiet_ids:
                return date_str
    return None


def main() -> None:
    sample_path = ROOT / "data/national_backtest_sample.json"
    events_path = ROOT / "data/national_events.json"
    output_dir = ROOT / "data/national_history"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not sample_path.exists():
        print("Missing data/national_backtest_sample.json")
        print("Run scripts/sample_backtest_events.py first.")
        return
    if not events_path.exists():
        print("Missing data/national_events.json")
        print("Run scripts/build_national_event_db.py first.")
        return

    sample_events = json.loads(sample_path.read_text())
    all_events = json.loads(events_path.read_text())
    state_dates: dict[str, set[str]] = defaultdict(set)
    for event in all_events:
        state_dates[event["state"]].add(event["date"])

    stations = load_station_catalog()
    pulled_severe = 0
    pulled_quiet = 0
    used_quiet_ids = set()

    for event in sample_events:
        event_output = output_dir / f"event_{event['event_id']}.json"
        if event_output.exists():
            pulled_severe += 1
            continue

        lat = float(event["begin_lat"])
        lon = float(event["begin_lon"])
        event_dt = _dt(event["event_datetime_utc"])
        summary_start = event_dt - timedelta(days=10)
        observation_start = event_dt - timedelta(hours=12)

        chosen_station = None
        full_history = []
        for station in candidate_stations(lat, lon, stations):
            try:
                history = pull_iem_observations(station["icaoId"], summary_start, event_dt)
            except Exception:
                continue
            if len(history) >= 12:
                chosen_station = station
                full_history = history
                break

        if chosen_station is None:
            continue

        observations = [obs for obs in full_history if _dt(obs["timestamp"]) >= observation_start]
        payload = {
            **event,
            "station": chosen_station["icaoId"],
            "station_distance_miles": chosen_station["distance_miles"],
            "observation_count": len(observations),
            "observations": observations,
            "daily_summaries": build_daily_summaries(full_history),
            "upper_air": None,
        }
        event_output.write_text(json.dumps(payload, indent=2) + "\n")
        pulled_severe += 1
        print(f"[event] {event['event_id']} {event['event_type']} -> {chosen_station['icaoId']} ({len(observations)} obs)")
        time.sleep(0.2)

        if pulled_quiet >= 100:
            continue
        quiet_date = pick_quiet_date(event, state_dates, used_quiet_ids)
        if quiet_date is None:
            continue
        quiet_id = f"{quiet_date}_{event['event_id']}"
        used_quiet_ids.add(quiet_id)
        quiet_output = output_dir / f"quiet_{quiet_id}.json"
        if quiet_output.exists():
            pulled_quiet += 1
            continue

        quiet_dt = _dt(f"{quiet_date}T{event.get('time_utc') or '18:00'}:00Z")
        quiet_summary_start = quiet_dt - timedelta(days=10)
        quiet_obs_start = quiet_dt - timedelta(hours=12)
        try:
            quiet_history = pull_iem_observations(chosen_station["icaoId"], quiet_summary_start, quiet_dt)
        except Exception:
            continue
        quiet_observations = [obs for obs in quiet_history if _dt(obs["timestamp"]) >= quiet_obs_start]
        quiet_payload = {
            "quiet_id": quiet_id,
            "date": quiet_date,
            "state": event["state"],
            "sample_category": event["sample_category"],
            "station": chosen_station["icaoId"],
            "station_distance_miles": chosen_station["distance_miles"],
            "observation_count": len(quiet_observations),
            "observations": quiet_observations,
            "daily_summaries": build_daily_summaries(quiet_history),
            "upper_air": None,
        }
        quiet_output.write_text(json.dumps(quiet_payload, indent=2) + "\n")
        pulled_quiet += 1
        print(f"[quiet] {quiet_id} -> {chosen_station['icaoId']} ({len(quiet_observations)} obs)")
        time.sleep(0.2)

    print()
    print(f"Pulled severe fixtures: {pulled_severe}")
    print(f"Pulled quiet fixtures:  {pulled_quiet}")
    print(f"Saved under: {output_dir}")


if __name__ == "__main__":
    main()
