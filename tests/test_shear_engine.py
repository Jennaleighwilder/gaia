import sys

sys.path.insert(0, ".")

from runtime.engines.shear_engine import ShearEngine


def test_calm_day():
    engine = ShearEngine()
    result = engine.score("KTRI", wind_speed_mph=5.0, wind_gust_mph=6.0, wind_direction_deg=180.0)
    assert result["score"] < 0.1, result
    print("PASS: shear calm day")


def test_gusty_prefrontal():
    engine = ShearEngine()
    engine.ingest("KTRI", "2026-03-21T15:00:00Z", wind_speed_mph=15.0, wind_gust_mph=22.0, wind_direction_deg=170.0)
    engine.ingest("KTRI", "2026-03-21T16:00:00Z", wind_speed_mph=20.0, wind_gust_mph=32.0, wind_direction_deg=190.0)
    engine.ingest("KTRI", "2026-03-21T17:00:00Z", wind_speed_mph=22.0, wind_gust_mph=40.0, wind_direction_deg=215.0)
    result = engine.score("KTRI", wind_speed_mph=25.0, wind_gust_mph=45.0, wind_direction_deg=230.0)
    assert result["score"] > 0.5, result
    print("PASS: shear gusty prefrontal")


def test_convergence_zone():
    engine = ShearEngine()
    result = engine.score(
        "KTRI",
        wind_speed_mph=18.0,
        wind_gust_mph=28.0,
        wind_direction_deg=90.0,
        network_observations=[
            {"wind_speed_mph": 20.0, "wind_direction_deg": 270.0},
            {"wind_speed_mph": 16.0, "wind_direction_deg": 180.0},
        ],
    )
    assert result["channels"]["cross_station_convergence"] > 0.7, result
    print("PASS: shear convergence zone")


def test_wind_backing_rate():
    engine = ShearEngine()
    engine.ingest("KTRI", "2026-03-21T15:00:00Z", wind_speed_mph=15.0, wind_gust_mph=22.0, wind_direction_deg=250.0)
    engine.ingest("KTRI", "2026-03-21T16:00:00Z", wind_speed_mph=18.0, wind_gust_mph=26.0, wind_direction_deg=225.0)
    engine.ingest("KTRI", "2026-03-21T17:00:00Z", wind_speed_mph=20.0, wind_gust_mph=30.0, wind_direction_deg=205.0)
    result = engine.score("KTRI", wind_speed_mph=22.0, wind_gust_mph=34.0, wind_direction_deg=185.0)
    assert result["channels"]["wind_backing_rate"] > 0.5, result
    print("PASS: shear wind backing rate")


if __name__ == "__main__":
    test_calm_day()
    test_gusty_prefrontal()
    test_convergence_zone()
    test_wind_backing_rate()
    print("ALL SHEAR TESTS PASSED")
