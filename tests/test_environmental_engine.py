import sys

sys.path.insert(0, ".")

from runtime.engines.environmental_engine import EnvironmentalEngine


def test_healthy_region():
    engine = EnvironmentalEngine()
    result = engine.score(timestamp="2026-03-21T18:00:00Z", recent_event_severity=0.0, precip_7d_ratio=0.3, drought_class=0, stream_level_ratio=0.3)
    assert result["score"] < 0.15, result
    print("PASS: environmental healthy region")


def test_soil_saturated():
    engine = EnvironmentalEngine()
    result = engine.score(timestamp="2026-03-21T18:00:00Z", recent_event_severity=0.0, precip_7d_ratio=1.4, drought_class=0, stream_level_ratio=0.5)
    assert result["channels"]["soil_saturation_proxy"] > 0.5, result
    print("PASS: environmental soil saturated")


def test_recent_damage_plus_rain():
    engine = EnvironmentalEngine()
    result = engine.score(timestamp="2026-03-21T18:00:00Z", recent_event_severity=0.9, precip_7d_ratio=1.6, drought_class=0, stream_level_ratio=1.1)
    assert result["score"] > 0.6, result
    print("PASS: environmental recent damage plus rain")


if __name__ == "__main__":
    test_healthy_region()
    test_soil_saturated()
    test_recent_damage_plus_rain()
    print("ALL ENVIRONMENTAL TESTS PASSED")

