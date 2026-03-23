import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

from runtime.memory.event_memory import EventMemory


def test_event_memory_round_trip():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "event_memory.jsonl"
        memory = EventMemory(str(path))
        memory.record_prediction(
            {
                "region": "hawkins",
                "decision": "WARNING",
                "convergence_count": 4,
                "engine_scores": {"pressure": 0.7},
                "saddle_active": True,
                "motion_correlation": 0.4,
                "upper_air_available": True,
                "composite_stp": 1.2,
            }
        )
        predictions = memory.get_all_predictions()
        assert len(predictions) == 1, predictions
        assert predictions[0]["decision"] == "WARNING", predictions
        print("PASS: memory prediction round trip")


def test_event_memory_calibration():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "event_memory.jsonl"
        memory = EventMemory(str(path))
        memory.record_prediction({"region": "a", "decision": "WARNING"})
        memory.record_prediction({"region": "b", "decision": "WATCH"})
        memory.record_outcome("t1", {"was_correct": True, "was_false_alarm": False, "was_miss": False})
        memory.record_outcome("t2", {"was_correct": False, "was_false_alarm": True, "was_miss": False})
        stats = memory.compute_calibration()
        assert stats["correct"] == 1, stats
        assert stats["false_alarms"] == 1, stats
        assert round(stats["false_alarm_rate"], 4) == 0.5, stats
        print("PASS: memory calibration")


if __name__ == "__main__":
    test_event_memory_round_trip()
    test_event_memory_calibration()
    print("ALL EVENT MEMORY TESTS PASSED")
