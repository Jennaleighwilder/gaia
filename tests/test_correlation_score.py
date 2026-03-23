import sys

sys.path.insert(0, ".")

from runtime.engines.correlation_score import engine_correlation


ALARM_ENGINES = ["pressure", "thermal", "moisture", "shear", "instability", "historical_analog"]


def test_insufficient_history():
    score = engine_correlation(
        [{"pressure": 0.1, "thermal": 0.2}, {"pressure": 0.2, "thermal": 0.3}],
        ["pressure", "thermal"],
        window=4,
    )
    assert score == 0.0, score
    print("PASS: insufficient history")


def test_high_correlation_when_engines_rise_together():
    timeline = [
        {"pressure": 0.12, "thermal": 0.18, "moisture": 0.16, "shear": 0.08, "instability": 0.10, "historical_analog": 0.20},
        {"pressure": 0.18, "thermal": 0.24, "moisture": 0.22, "shear": 0.12, "instability": 0.15, "historical_analog": 0.26},
        {"pressure": 0.25, "thermal": 0.31, "moisture": 0.29, "shear": 0.18, "instability": 0.22, "historical_analog": 0.34},
        {"pressure": 0.33, "thermal": 0.40, "moisture": 0.37, "shear": 0.24, "instability": 0.30, "historical_analog": 0.43},
        {"pressure": 0.43, "thermal": 0.50, "moisture": 0.47, "shear": 0.31, "instability": 0.39, "historical_analog": 0.54},
    ]
    score = engine_correlation(timeline, ALARM_ENGINES, window=4)
    assert score >= 0.7, score
    print("PASS: correlated rise")


def test_low_correlation_for_mixed_motion():
    timeline = [
        {"pressure": 0.30, "thermal": 0.55, "moisture": 0.62, "shear": 0.18, "instability": 0.28, "historical_analog": 0.50},
        {"pressure": 0.31, "thermal": 0.52, "moisture": 0.64, "shear": 0.14, "instability": 0.29, "historical_analog": 0.50},
        {"pressure": 0.30, "thermal": 0.54, "moisture": 0.61, "shear": 0.17, "instability": 0.27, "historical_analog": 0.48},
        {"pressure": 0.32, "thermal": 0.53, "moisture": 0.62, "shear": 0.15, "instability": 0.30, "historical_analog": 0.47},
        {"pressure": 0.31, "thermal": 0.55, "moisture": 0.60, "shear": 0.16, "instability": 0.28, "historical_analog": 0.46},
    ]
    score = engine_correlation(timeline, ALARM_ENGINES, window=4)
    assert score <= 0.35, score
    print("PASS: mixed motion stays low")


if __name__ == "__main__":
    test_insufficient_history()
    test_high_correlation_when_engines_rise_together()
    test_low_correlation_for_mixed_motion()
    print("ALL CORRELATION SCORE TESTS PASSED")
