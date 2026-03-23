"""
GAIA Sensor Mesh Engine
Monitors network coherence, dropout, and expected signal propagation.
"""

from __future__ import annotations

import math

from runtime.engines.common import clamp, parse_timestamp
from runtime.ingest.noaa_client import STATIONS


def _haversine_miles(lat1, lon1, lat2, lon2):
    r = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class SensorMeshEngine:
    def __init__(self, stations: dict | None = None):
        self.stations = stations or STATIONS
        self.last_seen = {}
        self.propagation_windows = {}

    def ingest(self, station_id, timestamp, **data):
        self.last_seen[station_id] = timestamp

    def cross_validate(self, observations):
        anomalies = []
        for i, first in enumerate(observations):
            for second in observations[i + 1:]:
                if not first.get("station_id") or not second.get("station_id"):
                    continue
                pressure_a = first.get("pressure_mb")
                pressure_b = second.get("pressure_mb")
                if pressure_a is not None and pressure_b is not None and abs(pressure_a - pressure_b) > 8.0:
                    anomalies.append((first["station_id"], second["station_id"], "pressure_gradient"))
                temp_a = first.get("temperature_f")
                temp_b = second.get("temperature_f")
                if temp_a is not None and temp_b is not None and abs(temp_a - temp_b) > 25.0:
                    anomalies.append((first["station_id"], second["station_id"], "thermal_divergence"))
        return {"anomalies": anomalies, "count": len(anomalies)}

    def propagation_tracking(self, event_type: str, origin_station: str, timestamp: str):
        origin = self.stations[origin_station]
        start = parse_timestamp(timestamp)
        for station_id, info in self.stations.items():
            if station_id == origin_station:
                continue
            miles = _haversine_miles(origin["lat"], origin["lon"], info["lat"], info["lon"])
            min_hours = miles / 70.0
            max_hours = miles / 20.0
            self.propagation_windows[(event_type, origin_station, station_id)] = (
                start.timestamp() + min_hours * 3600.0,
                start.timestamp() + max_hours * 3600.0,
            )

    def score(self, station_id="network", **current_data):
        observations = current_data.get("observations", [])
        expected_station_ids = set(current_data.get("expected_station_ids") or self.stations.keys())
        observed = {obs.get("station_id") for obs in observations if obs.get("station_id")}
        for obs in observations:
            if obs.get("station_id") and obs.get("timestamp"):
                self.ingest(obs["station_id"], obs["timestamp"])
        dropout = len(expected_station_ids - observed)
        validation = self.cross_validate(observations)
        divergence_score = clamp(validation["count"] / 2.0)
        dropout_score = clamp(dropout / 2.0)
        weighted = (dropout_score * 0.6) + (divergence_score * 0.4)

        propagation_confirmed = False
        event_type = current_data.get("propagation_event_type")
        origin_station = current_data.get("origin_station")
        confirming_station = current_data.get("confirming_station")
        current_time = current_data.get("current_time")
        if event_type and origin_station and confirming_station and current_time:
            key = (event_type, origin_station, confirming_station)
            if key in self.propagation_windows:
                start_ts, end_ts = self.propagation_windows[key]
                now_ts = parse_timestamp(current_time).timestamp()
                propagation_confirmed = start_ts <= now_ts <= end_ts

        return {
            "engine": "sensor_mesh",
            "score": round(clamp(weighted), 4),
            "divergence_count": validation["count"],
            "propagation_confirmed": propagation_confirmed,
        }
