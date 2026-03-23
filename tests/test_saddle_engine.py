import sys

sys.path.insert(0, ".")

from runtime.engines.saddle_engine import SaddleEngine


def test_all_stable():
    engine = SaddleEngine()
    history = [
        {"pressure": 0.1, "thermal": 0.1, "moisture": 0.1},
        {"pressure": 0.1, "thermal": 0.1, "moisture": 0.1},
        {"pressure": 0.1, "thermal": 0.1, "moisture": 0.1},
    ]
    for idx, row in enumerate(history):
        engine.ingest("east_tn", f"2026-03-21T0{idx}:00:00Z", **row)
    result = engine.score("east_tn")
    assert result["score"] == 0.0, result
    print("PASS: saddle stable")


def test_three_engines_rising():
    engine = SaddleEngine()
    history = [
        {"pressure": 0.20, "thermal": 0.22, "moisture": 0.18},
        {"pressure": 0.25, "thermal": 0.27, "moisture": 0.24},
        {"pressure": 0.31, "thermal": 0.34, "moisture": 0.30},
    ]
    for idx, row in enumerate(history):
        engine.ingest("east_tn", f"2026-03-21T0{idx}:00:00Z", **row)
    result = engine.score("east_tn")
    assert result["score"] > 0.0, result
    print("PASS: saddle rising below threshold")


def test_five_engines_rising_fast():
    engine = SaddleEngine()
    history = [
        {"pressure": 0.18, "thermal": 0.20, "moisture": 0.22, "shear": 0.19, "instability": 0.21},
        {"pressure": 0.27, "thermal": 0.30, "moisture": 0.32, "shear": 0.29, "instability": 0.31},
        {"pressure": 0.40, "thermal": 0.44, "moisture": 0.46, "shear": 0.42, "instability": 0.45},
    ]
    for idx, row in enumerate(history):
        engine.ingest("east_tn", f"2026-03-21T0{idx}:00:00Z", **row)
    result = engine.score("east_tn")
    assert result["score"] > 0.5, result
    print("PASS: saddle fast multi-engine approach")

def test_past_saddle():
    engine = SaddleEngine()
    history = [
        {"pressure": 0.45, "thermal": 0.50, "moisture": 0.48},
        {"pressure": 0.62, "thermal": 0.64, "moisture": 0.65},
        {"pressure": 0.72, "thermal": 0.74, "moisture": 0.75},
    ]
    for idx, row in enumerate(history):
        engine.ingest("east_tn", f"2026-03-21T0{idx}:00:00Z", **row)
    result = engine.score("east_tn")
    assert result["score"] == 0.0, result
    print("PASS: saddle drops once event is visible")


if __name__ == "__main__":
    test_all_stable()
    test_three_engines_rising()
    test_five_engines_rising_fast()
    test_past_saddle()
    print("ALL SADDLE TESTS PASSED")
