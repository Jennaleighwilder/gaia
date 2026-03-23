import sys

sys.path.insert(0, ".")

from runtime.engines.instability_engine import InstabilityEngine


def test_stable_winter_day():
    engine = InstabilityEngine()
    result = engine.score(
        "KTRI",
        cape_jkg=100,
        cin_jkg=-150,
        temperature_f=35.0,
        dewpoint_f=20.0,
        text_description="Clear",
    )
    assert result["score"] < 0.15, result
    print("PASS: instability stable winter day")


def test_loaded_spring_afternoon():
    engine = InstabilityEngine()
    engine.ingest("KTRI", "2026-03-21T16:00:00Z", cin_jkg=-100, cape_jkg=1800)
    result = engine.score(
        "KTRI",
        cape_jkg=2500,
        cin_jkg=-25,
        temperature_f=84.0,
        dewpoint_f=67.0,
        text_description="Fair",
    )
    assert result["score"] > 0.6, result
    print("PASS: instability loaded spring afternoon")


def test_cumulonimbus_channel():
    engine = InstabilityEngine()
    result = engine.score("KTRI", text_description="Cumulonimbus overhead")
    assert result["channels"]["cloud_development"] == 1.0, result
    print("PASS: instability cloud development")


def test_phase_transition():
    engine = InstabilityEngine()
    engine.ingest("KTRI", "2026-03-21T15:00:00Z", cape_jkg=900, cin_jkg=-80)
    first = engine.score("KTRI", cape_jkg=1200, cin_jkg=-70, temperature_f=74.0, dewpoint_f=58.0)
    second = engine.score(
        "KTRI",
        cape_jkg=1800,
        cin_jkg=-40,
        temperature_f=80.0,
        dewpoint_f=64.0,
        trigger_events=["pressure_alert"],
    )
    assert first["phase"] == "DRIFT", first
    assert second["phase"] == "INSULT", second
    assert second["phase_transition"] == {"from": "DRIFT", "to": "INSULT"}, second
    print("PASS: instability phase transition")


def test_cloud_type_progression():
    engine = InstabilityEngine()
    engine.ingest("KTRI", "2026-03-21T12:00:00Z", text_description="Cirrus")
    engine.ingest("KTRI", "2026-03-21T13:00:00Z", text_description="Altocumulus")
    engine.ingest("KTRI", "2026-03-21T14:00:00Z", text_description="Towering cumulus")
    result = engine.score(
        "KTRI",
        text_description="Cumulonimbus",
        temperature_f=81.0,
        dewpoint_f=66.0,
        trigger_events=["pressure_alert"],
    )
    assert result["channels"]["cloud_type_progression"] > 0.3, result
    print("PASS: instability cloud type progression")


def test_winter_mode_signal():
    engine = InstabilityEngine()
    for i, temp in enumerate([43.0, 40.0, 37.0, 34.0]):
        engine.ingest("KTRI", f"2024-01-14T1{i}:53:00Z", temperature_f=temp, dewpoint_f=22.0, pressure_mb=1019.0)
    result = engine.score(
        "KTRI",
        timestamp="2024-01-15T04:53:00Z",
        temperature_f=33.0,
        dewpoint_f=19.0,
        pressure_mb=1019.0,
        humidity_pct=56.0,
        wind_direction_deg=320.0,
        text_description="Overcast",
    )
    assert result["score"] > 0.3, result
    print("PASS: instability winter mode signal")


if __name__ == "__main__":
    test_stable_winter_day()
    test_loaded_spring_afternoon()
    test_cumulonimbus_channel()
    test_phase_transition()
    test_cloud_type_progression()
    test_winter_mode_signal()
    print("ALL INSTABILITY TESTS PASSED")
