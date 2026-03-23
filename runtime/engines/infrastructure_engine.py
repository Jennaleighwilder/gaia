"""
GAIA Infrastructure Health Engine
Scores whether the weather-observing and alerting infrastructure is degrading.
"""

from __future__ import annotations

from runtime.engines.common import clamp, parse_timestamp

EXPECTED_STATIONS = {"KTRI", "KMOR", "KTYS", "KGKT"}


class InfrastructureEngine:
    def __init__(self, expected_stations=None):
        self.expected_stations = set(expected_stations or EXPECTED_STATIONS)
        self.last_seen = {}
        self.last_observations = {}

    def ingest(self, station_id, timestamp, **data):
        self.last_seen[station_id] = timestamp
        self.last_observations[station_id] = {"timestamp": timestamp, **data}

    def score(self, station_id="network", **current_data):
        observations = current_data.get("observations", [])
        expected_station_ids = set(current_data.get("expected_station_ids") or self.expected_stations)
        current_time = parse_timestamp(current_data.get("current_time"))
        alerts_api_ok = current_data.get("alerts_api_ok", True)
        observed_ids = {obs.get("station_id") for obs in observations if obs.get("station_id")}
        for obs in observations:
            if obs.get("station_id") and obs.get("timestamp"):
                payload = {k: v for k, v in obs.items() if k not in {"station_id", "timestamp"}}
                self.ingest(obs["station_id"], obs["timestamp"], **payload)

        missing = expected_station_ids - observed_ids
        dropout_score = clamp(len(missing) / 2.0)

        bad_fields = 0
        total_fields = 0
        for obs in observations:
            core = ["temperature_f", "dewpoint_f", "pressure_mb", "wind_speed_mph"]
            total_fields += len(core)
            bad_fields += sum(1 for field in core if obs.get(field) is None)
        data_quality_score = clamp((bad_fields / total_fields) * 3.0) if total_fields else 0.0

        stale_count = 0
        for station_id in expected_station_ids:
            seen = self.last_seen.get(station_id)
            if not seen:
                continue
            minutes = (current_time - parse_timestamp(seen)).total_seconds() / 60.0
            if minutes > 60:
                stale_count += 1
        latency_score = clamp(stale_count / max(1, len(expected_station_ids) - 1))

        alert_score = 0.0 if alerts_api_ok else 1.0
        power_proxy = clamp(len(missing) / 2.0) if len(missing) >= 2 else 0.0

        channels = {
            "station_dropout": dropout_score,
            "data_quality": data_quality_score,
            "response_latency": latency_score,
            "alert_infrastructure": alert_score,
            "power_proxy": power_proxy,
        }
        weighted = (
            channels["station_dropout"] * 0.30
            + channels["data_quality"] * 0.25
            + channels["response_latency"] * 0.20
            + channels["alert_infrastructure"] * 0.15
            + channels["power_proxy"] * 0.10
        )
        if len(expected_station_ids) > 1 and stale_count == len(expected_station_ids):
            weighted = max(weighted, 0.8)
        elif len(expected_station_ids) > 1 and stale_count >= len(expected_station_ids) - 1:
            weighted = max(weighted, 0.65)
        return {"engine": "infrastructure", "score": round(clamp(weighted), 4), "channels": channels, "missing_stations": sorted(missing)}
