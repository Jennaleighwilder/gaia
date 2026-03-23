import sys

sys.path.insert(0, ".")

from runtime.engines.regime_engine import RegimeEngine


def stable_day(day: int) -> dict:
    return {
        "date": f"2026-03-{day:02d}",
        "mean_pressure": 1018.0 + ((day % 2) * 0.2),
        "mean_temp": 58.0 + ((day % 2) * 0.3),
        "dominant_wind_dir": 190.0 + ((day % 3) * 4.0),
        "precip_total": 0.0,
        "temp_range": 9.0,
    }


def breaking_day(day: int) -> dict:
    return {
        "date": f"2026-03-{day:02d}",
        "mean_pressure": 1018.0 - (day * 1.5),
        "mean_temp": 58.0 + (day * 3.0),
        "dominant_wind_dir": (30.0 + day * 55.0) % 360,
        "precip_total": 0.4 * day,
        "temp_range": 12.0 + day,
    }


def test_regime_insufficient_history():
    engine = RegimeEngine()
    result = engine.detect_transition()
    assert result["score"] == 0.0, result
    print("PASS: regime insufficient history")


def test_regime_stable_pattern():
    engine = RegimeEngine()
    for day in range(1, 12):
        engine.add_daily_summary(stable_day(day))
    result = engine.detect_transition()
    assert result["score"] <= 0.15, result
    print("PASS: regime stable pattern")


def test_regime_breaking_pattern():
    engine = RegimeEngine()
    for day in range(1, 8):
        engine.add_daily_summary(stable_day(day))
    for day in range(8, 15):
        engine.add_daily_summary(breaking_day(day - 7))
    result = engine.detect_transition()
    assert result["score"] >= 0.45, result
    print("PASS: regime breaking pattern")


if __name__ == "__main__":
    test_regime_insufficient_history()
    test_regime_stable_pattern()
    test_regime_breaking_pattern()
    print("ALL REGIME TESTS PASSED")
