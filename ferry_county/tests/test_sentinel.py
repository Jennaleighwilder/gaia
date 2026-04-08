from __future__ import annotations

import os

import pytest
from sqlalchemy import text

import backend.models  # noqa: F401
from backend.config import reset_settings_cache
from backend.database import Base, get_engine, get_session_factory, reset_engine
from backend.main import app
from backend.services.sentinel import (
    ATMOSPHERE_THRESHOLD,
    CANOPY_THRESHOLD,
    calculate_road_risk_score,
    fetch_canopy_signal,
    run_convergence_scan,
)


def _ground(palmer: float = -0.5) -> dict:
    return {
        "palmer_drought_index": palmer,
        "watershed_stress": 0.2,
        "slope_fire_risk_index": 68.0,
        "soil_moisture_pct": 40.0,
        "snotel_swe_pct_normal": 80.0,
    }


def _canopy(fuel: float, regrowth: float = 0.1) -> dict:
    return {"fuel_load_score": fuel, "regrowth_factor": regrowth}


def test_convergence_count_zero():
    atmos = {"fire_weather_index": 40.0, "red_flag_active": False}
    canopy = _canopy(50.0, 0.1)
    ground = _ground(0.0)
    r = calculate_road_risk_score(1, atmos, canopy, ground)
    assert r["convergence_count"] == 0
    assert r["risk_level"] == "low"


def test_convergence_count_one():
    atmos = {"fire_weather_index": float(ATMOSPHERE_THRESHOLD + 5), "red_flag_active": False}
    canopy = _canopy(45.0, 0.1)
    ground = _ground(0.0)
    r = calculate_road_risk_score(1, atmos, canopy, ground)
    assert r["convergence_count"] == 1
    assert r["risk_level"] == "moderate"


def test_convergence_count_two():
    atmos = {"fire_weather_index": float(ATMOSPHERE_THRESHOLD + 1), "red_flag_active": False}
    canopy = _canopy(55.0, 0.1)
    ground = _ground(-1.0)
    r = calculate_road_risk_score(1, atmos, canopy, ground)
    assert r["convergence_count"] == 2
    assert r["risk_level"] == "elevated"


def test_convergence_count_three():
    atmos = {"fire_weather_index": 88.0, "red_flag_active": False}
    canopy = _canopy(55.0, 0.1)
    ground = _ground(-3.0)
    r = calculate_road_risk_score(1, atmos, canopy, ground)
    assert r["convergence_count"] == 3
    assert r["risk_level"] == "critical"


def test_primary_driver_attribution():
    atmos = {"fire_weather_index": 95.0, "red_flag_active": False}
    canopy = _canopy(20.0, 0.1)
    ground = _ground(-0.5)
    r = calculate_road_risk_score(9, atmos, canopy, ground)
    assert r["primary_driver"] == "atmosphere"

    atmos2 = {"fire_weather_index": 40.0, "red_flag_active": False}
    canopy2 = _canopy(80.0, 0.5)
    r2 = calculate_road_risk_score(9, atmos2, canopy2, ground)
    assert r2["primary_driver"] == "canopy"


def test_recommendation_language():
    atmos = {"fire_weather_index": 90.0, "red_flag_active": False}
    canopy = _canopy(60.0, 0.2)
    ground = _ground(-4.0)
    r = calculate_road_risk_score(1, atmos, canopy, ground)
    assert len(r["recommendation"] or "") > 20


def test_red_flag_forces_critical():
    atmos = {"fire_weather_index": 20.0, "red_flag_active": True}
    canopy = _canopy(20.0, 0.1)
    ground = _ground(0.0)
    r = calculate_road_risk_score(1, atmos, canopy, ground)
    assert r["convergence_count"] == 0
    assert r["risk_level"] == "critical"


@pytest.mark.integration
def test_empty_road_list_scan_and_history(
    postgres_ready: bool,
    database_url: str,
) -> None:
    if not postgres_ready:
        pytest.skip("Postgres not reachable")
    os.environ["DATABASE_URL"] = database_url
    reset_settings_cache()
    reset_engine()
    engine = get_engine()
    with engine.connect() as c:
        c.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        c.commit()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        assert fetch_canopy_signal(db) == []
        out = run_convergence_scan(db)
        assert out["road_count"] == 0
    finally:
        db.close()

    from fastapi.testclient import TestClient

    client = TestClient(app)
    h = client.get("/sentinel/history/1")
    assert h.status_code in (404, 200)
