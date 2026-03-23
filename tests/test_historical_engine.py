import sys

sys.path.insert(0, ".")

from runtime.engines.historical_engine import HistoricalEngine


def test_no_match():
    engine = HistoricalEngine()
    result = engine.score(
        "KTRI",
        timestamp="2026-01-15T18:00:00Z",
        temperature_f=35.0,
        dewpoint_f=15.0,
        wind_direction_deg=20.0,
        wind_speed_mph=5.0,
        pressure_mb=1022.0,
    )
    assert result["score"] == 0.0, result
    print("PASS: historical no match")


def test_classic_southeast():
    engine = HistoricalEngine()
    engine.ingest("KTRI", "2026-03-21T16:00:00Z", pressure_mb=1012.0)
    engine.ingest("KTRI", "2026-03-21T17:00:00Z", pressure_mb=1010.5)
    result = engine.score(
        "KTRI",
        timestamp="2026-03-21T18:00:00Z",
        dewpoint_f=63.0,
        wind_direction_deg=210.0,
        wind_speed_mph=18.0,
        pressure_mb=1009.0,
    )
    assert result["score"] > 0.5, result
    print("PASS: historical classic southeast")


def test_summer_pulse():
    engine = HistoricalEngine()
    result = engine.score(
        "KTRI",
        timestamp="2026-07-10T18:00:00Z",
        dewpoint_f=70.0,
        temperature_f=92.0,
        wind_speed_mph=6.0,
        wind_direction_deg=180.0,
        pressure_mb=1012.0,
    )
    assert result["score"] > 0.3, result
    print("PASS: historical summer pulse")


def test_winter_heavy_snow_analog():
    engine = HistoricalEngine()
    result = engine.score(
        "KTYS",
        timestamp="2024-01-15T00:53:00Z",
        temperature_f=38.0,
        dewpoint_f=19.0,
        wind_speed_mph=0.0,
        wind_direction_deg=0.0,
        pressure_mb=1020.9,
    )
    assert result["score"] >= 0.6, result
    print("PASS: historical winter heavy snow analog")


if __name__ == "__main__":
    test_no_match()
    test_classic_southeast()
    test_summer_pulse()
    test_winter_heavy_snow_analog()
    print("ALL HISTORICAL TESTS PASSED")
