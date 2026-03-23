import sys

sys.path.insert(0, ".")

from runtime.engines.moisture_engine import MoistureEngine


def test_dry_day():
    engine = MoistureEngine()
    result = engine.score("KTRI", dewpoint_f=30.0, humidity_pct=25.0)
    assert result["score"] < 0.1, result
    print("PASS: moisture dry day")


def test_tropical_air_mass():
    engine = MoistureEngine()
    for i in range(9):
        engine.ingest("KTRI", f"2026-03-21T{10+i}:00:00Z", dewpoint_f=64 + i * 0.5, humidity_pct=70 + i)
    result = engine.score(
        "KTRI",
        dewpoint_f=72.0,
        humidity_pct=85.0,
        precipitable_water_in=2.1,
        wind_direction_deg=180,
        network_observations=[{"dewpoint_f": 70.0, "wind_direction_deg": 150}, {"dewpoint_f": 71.0, "wind_direction_deg": 210}],
    )
    assert result["score"] > 0.8, result
    print("PASS: moisture tropical air mass")


def test_moisture_surge():
    engine = MoistureEngine()
    for i in range(9):
        engine.ingest("KTRI", f"2026-03-21T{10+i}:00:00Z", dewpoint_f=52.0 + (i * 0.2), humidity_pct=55.0)
    result = engine.score("KTRI", dewpoint_f=60.5, humidity_pct=70.0)
    assert result["channels"]["dewpoint_trend"] > 0.8, result
    print("PASS: moisture surge")


if __name__ == "__main__":
    test_dry_day()
    test_tropical_air_mass()
    test_moisture_surge()
    print("ALL MOISTURE TESTS PASSED")

