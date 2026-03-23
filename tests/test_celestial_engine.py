"""
Tests for GAIA Engine 15: CELESTIAL (Space Weather Forcing Engine)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from runtime.engines.celestial_engine import CelestialEngine


def test_quiet_sun():
    """Quiet space weather should score near zero."""
    engine = CelestialEngine()
    obs = {
        "kp_index": 1,
        "solar_wind_speed_kms": 350,
        "solar_wind_density_pcm3": 4,
        "imf_bz_nt": 2.0,
        "proton_flux_pfu": 1.0,
    }
    score = engine.score(obs)
    assert score < 0.1
    assert engine.metadata.get("kp_class") == "QUIET"
    print(f"  PASS: quiet sun score = {score}, class = {engine.metadata['kp_class']}")


def test_strong_storm():
    """G3 strong storm conditions."""
    engine = CelestialEngine()
    obs = {
        "kp_index": 7,
        "solar_wind_speed_kms": 650,
        "solar_wind_density_pcm3": 22,
        "imf_bz_nt": -12.0,
        "proton_flux_pfu": 50.0,
    }
    score = engine.score(obs)
    assert score > 0.6
    assert engine.metadata.get("kp_class") == "G3_STRONG"
    print(f"  PASS: strong storm score = {score}")


def test_extreme_storm():
    """G5 extreme geomagnetic storm."""
    engine = CelestialEngine()
    obs = {
        "kp_index": 9,
        "solar_wind_speed_kms": 900,
        "solar_wind_density_pcm3": 40,
        "imf_bz_nt": -30.0,
        "proton_flux_pfu": 5000.0,
    }
    score = engine.score(obs)
    assert score > 0.9
    assert engine.metadata.get("kp_class") == "G5_EXTREME"
    print(f"  PASS: extreme storm score = {score}")


def test_no_data():
    """Engine should return 0 with no data and no fetch capability."""
    engine = CelestialEngine(fetcher=lambda url: None)
    score = engine.score({})
    assert score == 0
    print(f"  PASS: no data score = {score}")


def test_partial_data():
    """Engine should handle partial observation."""
    engine = CelestialEngine()
    obs = {"kp_index": 6}
    score = engine.score(obs)
    assert score > 0
    assert engine.channels["kp_index"] > 0
    print(f"  PASS: partial data (Kp only) score = {score}")


def test_reset():
    """Reset should clear cache and state."""
    engine = CelestialEngine()
    engine._cache["test"] = "data"
    engine.channels = {"test": 0.5}
    engine.reset()
    assert len(engine._cache) == 0
    assert engine.channels == {}
    print("  PASS: reset clears state")


if __name__ == "__main__":
    print("Testing Celestial Engine...")
    test_quiet_sun()
    test_strong_storm()
    test_extreme_storm()
    test_no_data()
    test_partial_data()
    test_reset()
    print("\nAll Celestial Engine tests PASSED.")
