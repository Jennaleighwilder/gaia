"""
Tests for GAIA Engine 14: SIREN (Storm Infrasound & Resonance Engine)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from runtime.engines.siren_engine import SirenEngine, calculate_sound_speed


def test_sound_speed_calculation():
    """Sound speed increases with temperature and humidity."""
    cold_dry = calculate_sound_speed(0, 0)
    warm_humid = calculate_sound_speed(35, 95)
    assert warm_humid > cold_dry
    baseline = calculate_sound_speed(20, 0)
    assert 342 < baseline < 345
    print(f"  PASS: sound speed cold_dry={cold_dry:.1f} warm_humid={warm_humid:.1f} baseline={baseline:.1f}")


def test_quiet_atmosphere():
    """Quiet conditions should score near zero."""
    engine = SirenEngine(config={"sound_baseline_speed": 343.0})
    obs = {
        "altimeter_inhg": 30.10,
        "temperature_c": 10,
        "humidity_pct": 0,
        "wind_sustained_kt": 5,
        "wind_gust_kt": 7,
        "visibility_sm": 10,
        "pressure_trend_hpa_hr": 0,
        "has_thunder": False,
        "thunder_onset_minutes": None,
    }
    for _ in range(35):
        score = engine.score(obs)
    assert score < 0.15
    print(f"  PASS: quiet atmosphere score = {score}")


def test_thunder_precursor():
    """Thunder within 60 minutes should trigger the channel."""
    engine = SirenEngine()
    obs = {
        "altimeter_inhg": 29.80,
        "temperature_c": 25,
        "humidity_pct": 80,
        "wind_sustained_kt": 10,
        "wind_gust_kt": 15,
        "visibility_sm": 8,
        "pressure_trend_hpa_hr": -2.0,
        "has_thunder": True,
        "thunder_onset_minutes": 30,
    }
    for _ in range(35):
        score = engine.score(obs)
    assert engine.channels["thunder_precursor"] > 0
    print(f"  PASS: thunder precursor score = {engine.channels['thunder_precursor']}")


def test_gust_coherence():
    """Rising gust factor should trigger gust coherence channel."""
    engine = SirenEngine()
    base_obs = {
        "altimeter_inhg": 29.70,
        "temperature_c": 28,
        "humidity_pct": 75,
        "visibility_sm": 7,
        "pressure_trend_hpa_hr": -3.0,
        "has_thunder": False,
        "thunder_onset_minutes": None,
    }
    for gust_mult in [1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.5, 2.8, 3.0]:
        obs = {**base_obs, "wind_sustained_kt": 15, "wind_gust_kt": 15 * gust_mult}
        engine.score(obs)
    assert engine.channels["gust_coherence"] > 0
    print(f"  PASS: gust coherence score = {engine.channels['gust_coherence']:.3f}")


def test_gaia_obs_adapter():
    """GAIA format obs should work via auto-conversion."""
    from runtime.engines.siren_engine import gaia_obs_to_siren_obs

    gaia_obs = {
        "pressure_mb": 1013.25,
        "temperature_f": 68,
        "humidity_pct": 60,
        "wind_speed_mph": 10,
        "wind_gust_mph": 15,
        "visibility_mi": 10,
        "text_description": "thunder",
    }
    siren_obs = gaia_obs_to_siren_obs(gaia_obs)
    assert siren_obs["altimeter_inhg"] is not None
    assert siren_obs["temperature_c"] == 20.0
    assert siren_obs["has_thunder"] is True
    engine = SirenEngine()
    score = engine.score(gaia_obs)
    assert isinstance(score, (int, float))
    print(f"  PASS: GAIA obs adapter score = {score}")


def test_reset():
    """Reset should clear all state."""
    engine = SirenEngine()
    engine.pressure_history.append(29.5)
    engine.channels = {"test": 0.5}
    engine.reset()
    assert len(engine.pressure_history) == 0
    assert engine.channels == {}
    print("  PASS: reset clears state")


if __name__ == "__main__":
    print("Testing Siren Engine...")
    test_sound_speed_calculation()
    test_quiet_atmosphere()
    test_thunder_precursor()
    test_gust_coherence()
    test_gaia_obs_adapter()
    test_reset()
    print("\nAll Siren Engine tests PASSED.")
