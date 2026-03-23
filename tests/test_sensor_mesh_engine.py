import sys

sys.path.insert(0, ".")

from runtime.engines.sensor_mesh_engine import SensorMeshEngine


def obs(station_id, pressure=1012.0, temp=70.0, dew=60.0):
    return {"station_id": station_id, "pressure_mb": pressure, "temperature_f": temp, "dewpoint_f": dew, "timestamp": "2026-03-21T18:00:00Z"}


def test_consistent_network():
    engine = SensorMeshEngine()
    result = engine.score(observations=[obs("KTRI"), obs("KMOR", 1011.5, 69.0), obs("KTYS", 1012.2, 71.0), obs("KGKT", 1012.0, 68.0)])
    assert result["score"] < 0.1, result
    print("PASS: sensor mesh consistent network")


def test_divergent_station():
    engine = SensorMeshEngine()
    result = engine.score(observations=[obs("KTRI"), obs("KMOR", 998.0, 95.0), obs("KTYS", 1012.2, 71.0), obs("KGKT", 1012.0, 68.0)])
    assert result["score"] > 0.3, result
    print("PASS: sensor mesh divergent station")


def test_two_dropouts():
    engine = SensorMeshEngine()
    result = engine.score(observations=[obs("KTRI"), obs("KMOR")])
    assert result["score"] > 0.5, result
    print("PASS: sensor mesh two dropouts")


def test_propagation_confirmed():
    engine = SensorMeshEngine()
    engine.propagation_tracking("pressure_drop", "KTRI", "2026-03-21T18:00:00Z")
    result = engine.score(
        observations=[obs("KTRI"), obs("KGKT")],
        propagation_event_type="pressure_drop",
        origin_station="KTRI",
        confirming_station="KGKT",
        current_time="2026-03-21T19:20:00Z",
    )
    assert result["propagation_confirmed"] is True, result
    print("PASS: sensor mesh propagation confirmed")


if __name__ == "__main__":
    test_consistent_network()
    test_divergent_station()
    test_two_dropouts()
    test_propagation_confirmed()
    print("ALL SENSOR MESH TESTS PASSED")

