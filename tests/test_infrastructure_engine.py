import sys

sys.path.insert(0, ".")

from runtime.engines.infrastructure_engine import InfrastructureEngine


def obs(station_id, ts, temp=70.0, dew=60.0, pressure=1012.0, wind=10.0):
    return {
        "station_id": station_id,
        "timestamp": ts,
        "temperature_f": temp,
        "dewpoint_f": dew,
        "pressure_mb": pressure,
        "wind_speed_mph": wind,
    }


def test_all_normal():
    engine = InfrastructureEngine()
    observations = [
        obs("KTRI", "2026-03-21T18:00:00Z"),
        obs("KMOR", "2026-03-21T18:00:00Z"),
        obs("KTYS", "2026-03-21T18:00:00Z"),
        obs("KGKT", "2026-03-21T18:00:00Z"),
    ]
    result = engine.score(observations=observations, current_time="2026-03-21T18:20:00Z")
    assert result["score"] == 0.0, result
    print("PASS: infrastructure all normal")


def test_one_station_silent():
    engine = InfrastructureEngine()
    observations = [
        obs("KTRI", "2026-03-21T18:00:00Z"),
        obs("KTYS", "2026-03-21T18:00:00Z"),
        obs("KGKT", "2026-03-21T18:00:00Z"),
    ]
    result = engine.score(observations=observations, current_time="2026-03-21T18:20:00Z")
    assert 0.12 <= result["score"] <= 0.2, result
    print("PASS: infrastructure one station silent")


def test_multiple_failures():
    engine = InfrastructureEngine()
    observations = [
        obs("KTRI", "2026-03-21T18:00:00Z", temp=None, dew=None, pressure=None, wind=10.0),
        obs("KTYS", "2026-03-21T18:00:00Z"),
    ]
    result = engine.score(observations=observations, current_time="2026-03-21T18:20:00Z")
    assert result["score"] > 0.5, result
    print("PASS: infrastructure multiple failures")


def test_all_stale():
    engine = InfrastructureEngine()
    observations = [
        obs("KTRI", "2026-03-21T16:00:00Z"),
        obs("KMOR", "2026-03-21T16:00:00Z"),
        obs("KTYS", "2026-03-21T16:00:00Z"),
        obs("KGKT", "2026-03-21T16:00:00Z"),
    ]
    result = engine.score(observations=observations, current_time="2026-03-21T18:20:00Z")
    assert result["score"] > 0.7, result
    print("PASS: infrastructure all stale")


if __name__ == "__main__":
    test_all_normal()
    test_one_station_silent()
    test_multiple_failures()
    test_all_stale()
    print("ALL INFRASTRUCTURE TESTS PASSED")

