import sys

sys.path.insert(0, ".")

from runtime.governor.duration_predictor import DurationPredictor


def test_duration_classes():
    predictor = DurationPredictor()
    assert predictor.classify_duration(0.25, 4.0, 12.0) == "PROLONGED"
    assert predictor.classify_duration(0.5, 3.0, 6.0) == "SUSTAINED"
    assert predictor.classify_duration(1.4, 2.5, 2.0) == "MODERATE"
    assert predictor.classify_duration(3.2, 2.0, 0.5) == "BRIEF"
    print("PASS: duration predictor classes")


if __name__ == "__main__":
    test_duration_classes()
    print("ALL DURATION PREDICTOR TESTS PASSED")
