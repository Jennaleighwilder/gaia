from __future__ import annotations

import os
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

import backend.models  # noqa: F401 — register metadata for create_all

from backend.config import reset_settings_cache
from backend.database import Base, get_engine, get_session_factory, reset_engine
from backend.main import app
from backend.models.road import Road
from backend.services.seed_kmz import import_kmz_file
from backend.services.treatment_service import create_treatment


@pytest.mark.integration
def test_vertical_slice_end_to_end(minimal_kmz_path: str, postgres_ready: bool, database_url: str) -> None:
    if not postgres_ready:
        pytest.skip("Postgres not reachable — start docker compose and create ferry_test database")
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
    tid: int
    try:
        stats = import_kmz_file(db, minimal_kmz_path, actor="test")
        assert stats["inserted"] == 1
        road = db.execute(select(Road).limit(1)).scalar_one()
        rid = road.id
        t = create_treatment(
            db,
            road_id=rid,
            treatment_date=date(2026, 4, 1),
            miles_treated=0.5,
            treatment_type="brush_clear",
            contractor="Test Co",
            contractor_task_order="TO-1",
            contractor_invoice_amount=2500.0,
            logged_by="tester",
            match_documented=True,
            match_source="cash",
            match_amount=100.0,
            amount_federal=300.0,
            amount_match=100.0,
            davis_bacon_certified=False,
            davis_bacon_wage_rate=None,
            notes=None,
            actor="tester",
        )
        db.commit()
        tid = t.id
    finally:
        db.close()

    client = TestClient(app)
    r = client.get(f"/treatments/{tid}/reimbursement")
    assert r.status_code == 200
    body = r.json()
    assert body["compliance_flags"]["davis_bacon_warning"] is True
    assert body["road_source_feature_id"]

    gj = client.get("/gis/export/geojson")
    assert gj.status_code == 200
    assert gj.json()["type"] == "FeatureCollection"

    field_map = client.get("/roads/geojson")
    assert field_map.status_code == 200
    fmj = field_map.json()
    assert fmj["type"] == "FeatureCollection"
    assert len(fmj["features"]) == 1
    assert fmj["features"][0]["properties"]["is_grant_road"] is True
    assert fmj["features"][0]["properties"]["treatment_status"] == "partial"
    assert fmj["features"][0]["geometry"]["type"] == "MultiLineString"

    kmz = client.get("/gis/export/kmz")
    assert kmz.status_code == 200
    assert kmz.content[:2] == b"PK"

    # cleanup row references
    SessionLocal = get_session_factory()
    db2 = SessionLocal()
    try:
        db2.execute(text("DELETE FROM audit_log"))
        db2.execute(text("DELETE FROM treatments"))
        db2.execute(text("DELETE FROM roads"))
        db2.commit()
    finally:
        db2.close()
