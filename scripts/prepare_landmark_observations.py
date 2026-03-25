#!/usr/bin/env python3
"""Create minimal event_{event_id}.json observation fixtures for landmark backtests."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANDMARKS = ROOT / "tests/fixtures/landmark_events.json"
OUT_DIR = ROOT / "tests/fixtures/historical_observations_landmarks"


def _nearest_asos_station(lat: float, lon: float) -> str:
    data = json.loads((ROOT / "data" / "asos_stations.json").read_text())

    def dist(s: dict) -> float:
        dlat = float(s["lat"]) - lat
        dlon = float(s["lon"]) - lon
        return dlat * dlat + dlon * dlon

    return min(data, key=dist)["id"]


def synthetic_observations(station: str, event_dt: datetime, n_hours: int = 30) -> list[dict]:
    obs = []
    start = event_dt - timedelta(hours=n_hours)
    for i in range(n_hours + 1):
        ts = start + timedelta(hours=i)
        # Escalate instability / wind slightly toward event
        ramp = i / max(n_hours, 1)
        temp = 72 + int(15 * ramp)
        dew = 58 + int(10 * ramp)
        wspd = 8 + int(20 * ramp)
        metar = (
            f"{station} {ts.strftime('%d%H%M')}Z 220{min(wspd, 35):02d}KT "
            f"10SM BKN050 24/18 A2990"
        )
        obs.append(
            {
                "timestamp": ts.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "station_id": station,
                "metar": metar,
                "sky_condition": "BKN",
                "temperature_f": float(temp),
                "dewpoint_f": float(dew),
                "pressure_mb": 1010.0 - 2.5 * ramp,
                "wind_direction_deg": 220.0,
                "wind_speed_mph": float(wspd),
                "visibility_mi": 10.0,
                "precip_1h_in": 0.05 * ramp if i > n_hours - 6 else 0.0,
            }
        )
    return obs


def main() -> int:
    events = json.loads(LANDMARKS.read_text())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ev in events:
        eid = ev["event_id"]
        lat = float(ev.get("lat") or 0)
        lon = float(ev.get("lon") or 0)
        station = _nearest_asos_station(lat, lon) if lat and lon else "KORD"
        event_dt = datetime.fromisoformat(ev["event_datetime_utc"].replace("Z", "+00:00"))
        observations = synthetic_observations(station, event_dt)
        out = {
            "event_id": eid,
            "event_date": ev["date"],
            "event_datetime_utc": ev["event_datetime_utc"],
            "station": station,
            "county": ev.get("county", ""),
            "event_type": ev.get("event_type", "tornado"),
            "magnitude": ev.get("magnitude", ""),
            "observation_count": len(observations),
            "observations": observations,
        }
        p = OUT_DIR / f"event_{eid}.json"
        p.write_text(json.dumps(out, indent=2) + "\n")
        print(f"Wrote {p.name} ({len(observations)} obs, {station})")
    print(f"Done: {len(events)} files -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
