import sys

sys.path.insert(0, ".")

from runtime.engines.uvrk_engine import UVRKAtmosphericEngine, inverse_normal_cdf


def build_observation(idx: int, noisy: bool = False) -> dict:
    if not noisy:
        return {
            "pressure_mb": 1013.0 + ((idx % 2) * 0.1),
            "temperature_f": 70.0 + ((idx % 3) * 0.2),
            "dewpoint_f": 58.0 + ((idx % 2) * 0.2),
            "wind_speed_mph": 8.0 + ((idx % 3) * 0.3),
        }
    swing = (-1) ** idx
    return {
        "pressure_mb": 1013.0 + (swing * (idx % 5) * 1.4),
        "temperature_f": 70.0 + (swing * (idx % 6) * 3.0),
        "dewpoint_f": 58.0 + (swing * (idx % 4) * 2.0),
        "wind_speed_mph": 8.0 + (idx % 7) * 4.0,
    }


def test_inverse_normal_cdf_center():
    assert inverse_normal_cdf(0.5) == 0.0
    print("PASS: uvrk inverse normal center")


def test_uvrk_stable_series_scores_low():
    engine = UVRKAtmosphericEngine()
    for idx in range(40):
        engine.ingest(build_observation(idx, noisy=False))
    result = engine.score()
    assert result["score"] < 0.25, result
    print("PASS: uvrk stable series")


def test_uvrk_volatile_series_scores_higher():
    engine = UVRKAtmosphericEngine()
    for idx in range(20):
        engine.ingest(build_observation(idx, noisy=False))
    for idx in range(20, 60):
        engine.ingest(build_observation(idx, noisy=True))
    result = engine.score()
    assert result["score"] > 0.25, result
    assert "pressure_mb" in result["channels"] or "temperature_f" in result["channels"], result
    print("PASS: uvrk volatile series")


if __name__ == "__main__":
    test_inverse_normal_cdf_center()
    test_uvrk_stable_series_scores_low()
    test_uvrk_volatile_series_scores_higher()
    print("ALL UVRK TESTS PASSED")
