import sys
import tempfile
import json

sys.path.insert(0, ".")

from runtime.engines.oscillation_engine import OscillationEngine


def run_with_state(state):
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=True) as handle:
        json.dump(state, handle)
        handle.flush()
        engine = OscillationEngine(state_path=handle.name)
        return engine.score()


def test_neutral_state():
    result = run_with_state(
        {
            "enso": {"phase": "neutral"},
            "nao": {"phase": "neutral"},
            "pna": {"phase": "neutral"},
            "mjo": {"phase": 5, "amplitude": 1.0},
        }
    )
    assert 0.15 <= result["score"] <= 0.3, result
    print("PASS: oscillation neutral state")


def test_high_threat_state():
    result = run_with_state(
        {
            "enso": {"phase": "la_nina"},
            "nao": {"phase": "negative"},
            "pna": {"phase": "positive"},
            "mjo": {"phase": 3, "amplitude": 1.5},
        }
    )
    assert result["score"] > 0.7, result
    print("PASS: oscillation high threat")


def test_low_threat_state():
    result = run_with_state(
        {
            "enso": {"phase": "el_nino"},
            "nao": {"phase": "positive"},
            "pna": {"phase": "negative"},
            "mjo": {"phase": 7, "amplitude": 1.0},
        }
    )
    assert result["score"] <= 0.15, result
    print("PASS: oscillation low threat")


if __name__ == "__main__":
    test_neutral_state()
    test_high_threat_state()
    test_low_threat_state()
    print("ALL OSCILLATION TESTS PASSED")

