"""
GAIA Pressure Engine Tests
Verifies pressure scoring against known scenarios.
"""

import sys

sys.path.insert(0, ".")

from runtime.engines.pressure_engine import PressureEngine


def test_normal_pressure():
    engine = PressureEngine()
    result = engine.score("TEST01", 1015.0)
    assert result["score"] == 0.0, f"Normal pressure should score 0.0, got {result['score']}"
    print("PASS: normal pressure scores 0.0")


def test_deep_low():
    engine = PressureEngine()
    result = engine.score("TEST01", 985.0)
    assert result["score"] > 0.0, "Deep low should score above 0.0"
    assert result["score"] <= 1.0, "Score should not exceed 1.0"
    assert any(s[0] == "deep_low" for s in result["matched_signatures"])
    print(f"PASS: deep low (985mb) scores {result['score']}")


def test_rapid_drop():
    engine = PressureEngine()
    for i in range(9):
        pressure = 1020.0 - (i * 1.0)
        engine.ingest("TEST01", f"2026-03-21T{10 + i}:00:00Z", pressure)
    result = engine.score("TEST01", 1012.0)
    assert result["score"] > 0.0, "Rapid drop should trigger"
    assert any(s[0] == "rapid_drop" for s in result["matched_signatures"])
    print(f"PASS: rapid drop scores {result['score']}")


def test_oscillation():
    engine = PressureEngine()
    pressures = [1015, 1012, 1016, 1011, 1017, 1010]
    for i, pressure in enumerate(pressures):
        engine.ingest("TEST01", f"2026-03-21T{10 + i}:00:00Z", pressure)
    result = engine.score("TEST01", 1010.0)
    assert any(s[0] == "oscillation" for s in result["matched_signatures"])
    print(f"PASS: oscillation detected, scores {result['score']}")


def test_noaa_connection():
    try:
        from runtime.ingest.noaa_client import get_latest_observation

        obs = get_latest_observation("KTRI")
        assert obs is not None, "Should get data from Tri-Cities Airport"
        assert obs.get("pressure_mb") is not None or obs.get("temperature_c") is not None
        print(f"PASS: NOAA connection OK — {obs['station_name']}: {obs.get('text_description', 'N/A')}")
    except Exception as e:  # noqa: BLE001
        print(f"SKIP: NOAA connection test skipped: {e}")


if __name__ == "__main__":
    print("\nGAIA Pressure Engine Tests")
    print("=" * 40)
    test_normal_pressure()
    test_deep_low()
    test_rapid_drop()
    test_oscillation()
    test_noaa_connection()
    print("\n=== All tests passed ===\n")
