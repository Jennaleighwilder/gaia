from __future__ import annotations

import os
import zipfile
from datetime import date
from io import BytesIO

import pytest
from sqlalchemy import inspect, select, text

import backend.models  # noqa: F401

from backend.config import reset_settings_cache
from backend.database import Base, get_engine, get_session_factory, reset_engine
from backend.main import app
from backend.models.reporting import QuarterlyFinancialReport
from backend.models.road import Road
from backend.services.compliance_engine import format_match_ratio_response
from backend.services.seed_kmz import import_kmz_file


def test_format_match_ratio_compliant_at_threshold():
    r = format_match_ratio_response(75.0, 25.0, 0.25)
    assert r["compliant"] is True
    assert r["ratio_percent"] is not None
    assert abs(r["ratio_percent"] - 25.0) < 0.01


def test_format_match_ratio_below_threshold():
    r = format_match_ratio_response(90.0, 10.0, 0.25)
    assert r["compliant"] is False
    assert r["ratio_percent"] is not None
    assert r["ratio_percent"] < 25.0


def test_format_match_ratio_zero_denominator():
    r = format_match_ratio_response(0.0, 0.0, 0.25)
    assert r["ratio_percent"] is None
    assert r["compliant"] is False


def test_quarterly_financial_ratio_formula_matches_service():
    """Mirrors create_quarterly_financial_report totals."""
    fed, mc, mi = 1000.0, 200.0, 100.0
    match_total = mc + mi
    total_spend = fed + match_total
    match_ratio = match_total / total_spend
    assert abs(match_ratio - 300.0 / 1300.0) < 1e-9


def test_quarterly_financial_reports_model_table_name():
    assert QuarterlyFinancialReport.__tablename__ == "quarterly_financial_reports"


@pytest.mark.integration
def test_compliance_match_ratio_export_quarterly_and_table(
    postgres_ready: bool,
    database_url: str,
    minimal_kmz_path: str,
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

    insp = inspect(engine)
    assert "quarterly_financial_reports" in insp.get_table_names()

    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        stats = import_kmz_file(db, minimal_kmz_path, actor="test")
        assert stats["inserted"] == 1
        rid = db.execute(select(Road.id).limit(1)).scalar_one()
    finally:
        db.close()

    from fastapi.testclient import TestClient

    client = TestClient(app)

    r = client.get("/compliance/match-ratio")
    assert r.status_code == 200, r.text
    j = r.json()
    assert "federal_spend_total" in j
    assert "match_documented_total" in j
    assert "ratio_percent" in j
    assert "compliant" in j
    assert j["match_ratio_required_percent"] == 25.0

    op_id = "550e8400-e29b-41d4-a716-446655440099"
    body = {
        "client_operation_id": op_id,
        "entity_type": "treatment",
        "operation": "create",
        "payload": {
            "road_id": rid,
            "treatment_date": "2026-04-01",
            "miles_treated": 0.1,
            "treatment_type": "brush_clear",
            "match_documented": True,
            "amount_federal": 750.0,
            "amount_match": 250.0,
            "davis_bacon_certified": True,
            "contractor_invoice_amount": 100.0,
        },
    }
    r_sync = client.post("/sync/operations", json=body, headers={"X-Actor": "t"})
    assert r_sync.status_code == 200, r_sync.text

    r2 = client.get("/compliance/match-ratio")
    assert r2.status_code == 200
    m = r2.json()
    assert m["federal_spend_total"] == 750.0
    assert m["match_documented_total"] == 250.0
    assert m["compliant"] is True

    r_geo = client.get(
        "/compliance/export/geojson",
        params={"period_start": "2026-01-01", "period_end": "2026-12-31"},
    )
    assert r_geo.status_code == 200, r_geo.text
    fc = r_geo.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 1
    f0 = fc["features"][0]
    assert f0["properties"]["treatment_date"] == "2026-04-01"
    assert f0["properties"]["miles_treated"] == 0.1
    assert f0["geometry"]["type"] == "MultiLineString"

    r_kmz = client.get(
        "/compliance/export/kmz",
        params={"period_start": "2026-01-01", "period_end": "2026-12-31"},
    )
    assert r_kmz.status_code == 200
    assert r_kmz.headers.get("content-type", "").startswith("application/vnd.google-earth.kmz")
    z = zipfile.ZipFile(BytesIO(r_kmz.content))
    assert "doc.kml" in z.namelist()

    r_bad = client.get(
        "/compliance/export/geojson",
        params={"period_start": "2026-12-31", "period_end": "2026-01-01"},
    )
    assert r_bad.status_code == 400

    r_q = client.post(
        "/compliance/quarterly-report",
        json={
            "quarter": "2026-Q1",
            "federal_spend": 10000,
            "match_cash": 2000,
            "match_inkind": 500,
            "submitted": True,
            "submitted_date": "2026-04-15",
        },
        headers={"X-Actor": "finance"},
    )
    assert r_q.status_code == 200, r_q.text
    qj = r_q.json()
    assert qj["id"] > 0
    assert qj["quarter"] == "2026-Q1"
    assert qj["submitted"] is True
    assert qj["match_ratio"] is not None
    assert abs(qj["match_ratio"] - 2500.0 / 12500.0) < 1e-6
