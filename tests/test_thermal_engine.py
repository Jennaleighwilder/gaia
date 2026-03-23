import sys

sys.path.insert(0, ".")

from runtime.engines.thermal_engine import ThermalEngine


def test_normal_march_day():
    engine = ThermalEngine()
    result = engine.score("KTRI", timestamp="2026-03-21T18:00:00Z", temperature_f=58.0, dewpoint_f=38.0, humidity_pct=45)
    assert result["score"] < 0.15, result
    print("PASS: thermal normal March day")


def test_hot_humid_march_day():
    engine = ThermalEngine()
    result = engine.score(
        "KTRI",
        timestamp="2026-03-21T18:00:00Z",
        temperature_f=92.0,
        dewpoint_f=72.0,
        humidity_pct=70,
        overnight_low_f=68.0,
    )
    assert result["score"] > 0.7, result
    print("PASS: thermal hot humid day")


def test_frontal_contrast_channel():
    engine = ThermalEngine()
    result = engine.score(
        "KTRI",
        timestamp="2026-03-21T18:00:00Z",
        temperature_f=75.0,
        dewpoint_f=60.0,
        humidity_pct=60,
        network_observations=[{"temperature_f": 55.0, "dewpoint_f": 50.0}],
    )
    assert result["channels"]["frontal_contrast"] > 0.8, result
    print("PASS: thermal frontal contrast")


def test_overnight_no_cooling():
    engine = ThermalEngine()
    result = engine.score(
        "KTRI",
        timestamp="2026-03-21T18:00:00Z",
        temperature_f=78.0,
        dewpoint_f=65.0,
        humidity_pct=65,
        overnight_low_f=68.0,
    )
    assert result["channels"]["overnight_low_departure"] > 0.8, result
    print("PASS: thermal overnight low departure")


def test_winter_freezing_profile():
    engine = ThermalEngine()
    for i, temp in enumerate([41.0, 39.0, 37.0, 34.0]):
        engine.ingest("KTRI", f"2024-01-14T0{8+i}:53:00Z", temperature_f=temp, dewpoint_f=22.0, humidity_pct=70.0)
    result = engine.score(
        "KTRI",
        timestamp="2024-01-15T00:53:00Z",
        temperature_f=33.0,
        dewpoint_f=21.0,
        humidity_pct=61.0,
        pressure_mb=1019.5,
    )
    assert result["channels"]["freezing_rain_profile"] > 0.4, result
    print("PASS: thermal winter freezing profile")


if __name__ == "__main__":
    test_normal_march_day()
    test_hot_humid_march_day()
    test_frontal_contrast_channel()
    test_overnight_no_cooling()
    test_winter_freezing_profile()
    print("ALL THERMAL TESTS PASSED")
