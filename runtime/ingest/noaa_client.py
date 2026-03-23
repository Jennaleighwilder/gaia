"""
GAIA NOAA Data Ingest Client
Pulls real-time observations from api.weather.gov (free, no key needed).
Publishes to the GAIA event bus as observation events when requested.
"""

from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from typing import Optional

from runtime.physics.atmospheric_core import celsius_to_fahrenheit

STATIONS = {
    "KTRI": {
        "name": "Tri-Cities Airport",
        "county": "sullivan",
        "lat": 36.4752,
        "lon": -82.4074,
    },
    "KMOR": {
        "name": "Morristown Municipal",
        "county": "hamblen",
        "lat": 36.1794,
        "lon": -83.3755,
    },
    "KTYS": {
        "name": "McGhee Tyson Airport",
        "county": "blount",
        "lat": 35.8108,
        "lon": -83.9940,
    },
    "KGKT": {
        "name": "Gatlinburg-Pigeon Forge",
        "county": "sevier",
        "lat": 35.8578,
        "lon": -83.5287,
    },
}

BASE_URL = "https://api.weather.gov"
HEADERS = {
    "User-Agent": "(GAIA Weather Engine, theforgottencode780@gmail.com)",
    "Accept": "application/geo+json",
}


def _fetch(url: str) -> Optional[dict]:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[GAIA ingest] Error fetching {url}: {e}")
        return None


def get_latest_observation(station_id: str) -> Optional[dict]:
    url = f"{BASE_URL}/stations/{station_id}/observations/latest"
    data = _fetch(url)
    if not data or "properties" not in data:
        return None

    props = data["properties"]

    def _val(field_name: str):
        obj = props.get(field_name)
        if isinstance(obj, dict):
            return obj.get("value")
        return obj

    return {
        "station_id": station_id,
        "station_name": STATIONS.get(station_id, {}).get("name", station_id),
        "county": STATIONS.get(station_id, {}).get("county", "unknown"),
        "timestamp": props.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "temperature_c": _val("temperature"),
        "dewpoint_c": _val("dewpoint"),
        "pressure_mb": _val("barometricPressure"),
        "wind_speed_ms": _val("windSpeed"),
        "wind_direction_deg": _val("windDirection"),
        "wind_gust_ms": _val("windGust"),
        "visibility_m": _val("visibility"),
        "humidity_pct": _val("relativeHumidity"),
        "precipitation_1h_mm": _val("precipitationLastHour"),
        "text_description": _val("textDescription"),
    }


def normalize_observation(raw: dict) -> dict:
    obs = dict(raw)
    if obs.get("pressure_mb") is not None:
        obs["pressure_mb"] = obs["pressure_mb"] / 100.0
    if obs.get("temperature_c") is not None:
        obs["temperature_f"] = celsius_to_fahrenheit(obs["temperature_c"])
    if obs.get("dewpoint_c") is not None:
        obs["dewpoint_f"] = celsius_to_fahrenheit(obs["dewpoint_c"])
    if obs.get("wind_speed_ms") is not None:
        obs["wind_speed_mph"] = obs["wind_speed_ms"] * 2.237
        obs["wind_speed_kts"] = obs["wind_speed_ms"] * 1.944
    if obs.get("wind_gust_ms") is not None:
        obs["wind_gust_mph"] = obs["wind_gust_ms"] * 2.237
    if obs.get("visibility_m") is not None:
        obs["visibility_mi"] = obs["visibility_m"] / 1609.34
    return obs


def get_active_alerts(state: str = "TN") -> list:
    url = f"{BASE_URL}/alerts/active?area={state}"
    data = _fetch(url)
    if not data or "features" not in data:
        return []
    alerts = []
    for feature in data["features"]:
        props = feature.get("properties", {})
        alerts.append(
            {
                "event": props.get("event"),
                "severity": props.get("severity"),
                "certainty": props.get("certainty"),
                "urgency": props.get("urgency"),
                "headline": props.get("headline"),
                "description": (props.get("description") or "")[:500],
                "areas": props.get("areaDesc"),
                "onset": props.get("onset"),
                "expires": props.get("expires"),
            }
        )
    return alerts


def poll_all_stations() -> list:
    observations = []
    for station_id in STATIONS:
        raw = get_latest_observation(station_id)
        if raw:
            observations.append(normalize_observation(raw))
        time.sleep(5)
    return observations


def _fmt(value, suffix="", digits=1):
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}{suffix}"


if __name__ == "__main__":
    print("GAIA NOAA Ingest — Testing connection...")
    print()
    for station_id, info in STATIONS.items():
        print(f"Station: {station_id} ({info['name']}, {info['county']} county)")
        raw = get_latest_observation(station_id)
        if raw:
            obs = normalize_observation(raw)
            print(f"  Temp: {_fmt(obs.get('temperature_f'), '°F')}")
            print(f"  Dewpoint: {_fmt(obs.get('dewpoint_f'), '°F')}")
            print(f"  Pressure: {_fmt(obs.get('pressure_mb'), ' mb')}")
            wind_dir = obs.get("wind_direction_deg")
            print(f"  Wind: {_fmt(obs.get('wind_speed_mph'), ' mph')} from {wind_dir if wind_dir is not None else 'N/A'}°")
            print(f"  Humidity: {_fmt(obs.get('humidity_pct'), '%', 0)}")
            print(f"  Conditions: {obs.get('text_description') or 'N/A'}")
        else:
            print("  *** FAILED TO FETCH ***")
        print()
        time.sleep(5)

    print("Active TN alerts:")
    alerts = get_active_alerts("TN")
    if alerts:
        for alert in alerts:
            print(f"  [{alert.get('severity')}] {alert.get('event')}: {alert.get('headline')}")
    else:
        print("  No active alerts.")

    print()
    print("GAIA NOAA Ingest — Connection test complete.")
