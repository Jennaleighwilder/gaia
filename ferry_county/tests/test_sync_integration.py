from __future__ import annotations

import os
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

import backend.models  # noqa: F401

from backend.config import reset_settings_cache
from backend.database import Base, get_engine, get_session_factory, reset_engine
from backend.main import app
from backend.models.road import Road
from backend.services.seed_kmz import import_kmz_file


@pytest.mark.integration
def test_sync_treatment_create_idempotent(
    minimal_kmz_path: str,
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
        stats = import_kmz_file(db, minimal_kmz_path, actor="test")
        assert stats["inserted"] == 1
        rid = db.execute(select(Road.id).limit(1)).scalar_one()
    finally:
        db.close()

    client = TestClient(app)
    op_id = "550e8400-e29b-41d4-a716-446655440001"
    body_base = {
        "client_operation_id": op_id,
        "entity_type": "treatment",
        "operation": "create",
        "payload": {
            "road_id": rid,
            "treatment_date": "2026-04-08",
            "miles_treated": 0.05,
            "treatment_type": "brush_clear",
            "match_documented": True,
            "amount_federal": 75.0,
            "amount_match": 25.0,
            "davis_bacon_certified": True,
            "contractor_invoice_amount": 100.0,
        },
    }

    r1 = client.post("/sync/operations", json=body_base, headers={"X-Actor": "sync-test"})
    assert r1.status_code == 200, r1.text
    j1 = r1.json()
    assert j1["status"] == "applied"
    assert j1["result"]["treatment_id"] > 0
    tid = j1["result"]["treatment_id"]

    r2 = client.post("/sync/operations", json=body_base, headers={"X-Actor": "sync-test"})
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2["status"] == "duplicate"
    assert j2["result"]["treatment_id"] == tid

    body_conflict = {
        **body_base,
        "payload": {**body_base["payload"], "miles_treated": 0.99},
    }
    r3 = client.post("/sync/operations", json=body_conflict)
    assert r3.status_code == 409

    r4 = client.post(
        "/sync/operations",
        json={
            "client_operation_id": "660e8400-e29b-41d4-a716-446655440002",
            "entity_type": "unicorn",
            "operation": "fly",
            "payload": {},
        },
    )
    assert r4.status_code == 400

    db2 = SessionLocal()
    try:
        db2.execute(text("DELETE FROM reconciliation_log"))
        db2.execute(text("DELETE FROM sync_operations"))
        db2.execute(text("DELETE FROM audit_log"))
        db2.execute(text("DELETE FROM treatments"))
        db2.execute(text("DELETE FROM roads"))
        db2.commit()
    finally:
        db2.close()
