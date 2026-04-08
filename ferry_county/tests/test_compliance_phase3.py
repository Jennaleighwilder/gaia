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
from backend.models.waypoint import Waypoint
from backend.services.acreage import calculate_acres
from backend.services.compliance_engine import generate_invoice_support, generate_semi_annual_report
from backend.services.invoice_support_pdf import build_invoice_support_csv, build_invoice_support_pdf
from backend.services.seed_kmz import import_kmz_file
from backend.services.treatment_service import create_treatment


def test_invoice_pdf_cover_official_headers():
    data = {
        "period_start": "2026-01-01",
        "period_end": "2026-06-30",
        "line_items": [],
        "totals": {
            "treatment_count": 0,
            "total_miles": 0.0,
            "total_acres": 0.0,
            "total_federal_claimed": 12500.50,
        },
    }
    pdf = build_invoice_support_pdf(data)
    assert pdf.startswith(b"%PDF")
    assert b"Ferry County, Washington" in pdf
    assert b"Fuel Reduction Program" in pdf
    assert b"Billing period" in pdf
    assert b"David R. Vitelle" in pdf
    assert b"Steven L. Bonner" in pdf
    assert len(pdf) > 800


def test_invoice_csv_has_header_and_totals_row():
    data = {
        "period_start": "2026-01-01",
        "period_end": "2026-06-30",
        "line_items": [
            {
                "treatment_id": 1,
                "road_name": "Main",
                "road_number": "001",
                "district": 1,
                "treatment_date": "2026-04-01",
                "treatment_type": "brush_clear",
                "miles_treated": 1.0,
                "acres_treated": 3.636364,
                "gps_start": {"lat": 48.5, "lon": -118.0},
                "gps_end": {"lat": 48.51, "lon": -118.01},
                "contractor": "Co",
                "contractor_task_order": "TO-1",
                "match_documented": True,
                "amount_federal": 100.0,
            }
        ],
        "totals": {
            "treatment_count": 1,
            "total_miles": 1.0,
            "total_acres": 3.636364,
            "total_federal_claimed": 100.0,
        },
    }
    raw = build_invoice_support_csv(data).decode("utf-8")
    assert "treatment_id" in raw.splitlines()[0]
    assert "Main" in raw
    assert "TOTALS" in raw


def test_acreage_one_mile_matches_corridor_formula():
    assert abs(calculate_acres(1.0, 15.0) - 3.6363636363636362) < 1e-6


@pytest.mark.integration
def test_phase3_reports_period_filter_and_fields(
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

    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        stats = import_kmz_file(db, minimal_kmz_path, actor="test")
        assert stats["inserted"] == 1
        rid = db.execute(select(Road.id).limit(1)).scalar_one()
        create_treatment(
            db,
            road_id=rid,
            treatment_date=date(2026, 4, 15),
            miles_treated=1.0,
            treatment_type="brush_clear",
            contractor="Test Excavation",
            contractor_task_order="TO-99",
            contractor_invoice_amount=500.0,
            logged_by="t",
            match_documented=True,
            match_source="cash",
            match_amount=50.0,
            amount_federal=200.0,
            amount_match=50.0,
            davis_bacon_certified=False,
            davis_bacon_wage_rate=None,
            notes=None,
            actor="t",
        )
        db.add(
            Waypoint(
                waypoint_type="sign",
                label="S1",
                lat=48.5,
                lon=-118.0,
                buy_america_certified=True,
                created_by="t",
                updated_by="t",
            )
        )
        db.add(
            Waypoint(
                waypoint_type="mile_marker",
                label="MM1",
                lat=48.51,
                lon=-118.01,
                buy_america_certified=False,
                material_cost=25.0,
                vendor="V",
                created_by="t",
                updated_by="t",
            )
        )
        db.commit()
    finally:
        db.close()

    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        empty = generate_semi_annual_report(db, date(2010, 1, 1), date(2010, 1, 31))
        assert empty["total_miles_treated"] == 0.0
        assert empty["total_acres_treated"] == 0.0
        assert empty["roads_completed_count"] == 0
        assert empty["treatments"] == []
        assert empty["waypoints_summary"]["signs_placed"] == 0

        rep = generate_semi_annual_report(db, date(2026, 4, 1), date(2026, 4, 30))
        assert rep["total_miles_treated"] == 1.0
        assert abs(rep["total_acres_treated"] - calculate_acres(1.0)) < 1e-4
        assert rep["roads_partial_count"] >= 1 or rep["roads_completed_count"] >= 1
        assert len(rep["treatments"]) == 1
        tr = rep["treatments"][0]
        assert tr["road_name"]
        assert tr["treatment_date"] == "2026-04-15"
        assert tr["contractor"] == "Test Excavation"
        assert rep["match_ratio"]["federal_spend_total"] == 200.0
        assert rep["match_ratio"]["match_documented_total"] == 50.0
        assert rep["waypoints_summary"]["signs_placed"] == 1
        assert rep["waypoints_summary"]["mile_markers_placed"] == 1
        assert rep["compliance_flags"]["buy_america_missing_count"] == 1

        inv = generate_invoice_support(db, date(2026, 4, 1), date(2026, 4, 30))
        assert inv["totals"]["treatment_count"] == 1
        assert inv["totals"]["total_federal_claimed"] == 200.0
        assert inv["line_items"][0]["match_documented"] is True
        assert inv["line_items"][0]["contractor_task_order"] == "TO-99"
        assert "miles_treated" in inv["line_items"][0]
    finally:
        db.close()

    client = TestClient(app)
    r = client.get(
        "/compliance/invoice-support",
        params={"start": "2026-04-01", "end": "2026-04-30", "format": "pdf"},
    )
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content.startswith(b"%PDF")

    r2 = client.get(
        "/compliance/invoice-support",
        params={"start": "2026-04-01", "end": "2026-04-30", "format": "csv"},
    )
    assert r2.status_code == 200
    assert b"treatment_id" in r2.content

    r3 = client.get(
        "/compliance/semi-annual-report",
        params={"period_start": "2026-04-01", "period_end": "2026-04-30"},
    )
    assert r3.status_code == 200
    assert r3.json()["total_miles_treated"] == 1.0

    engine = get_engine()
    with engine.connect() as c:
        c.execute(text("DELETE FROM waypoints"))
        c.execute(text("DELETE FROM treatments"))
        c.execute(text("DELETE FROM roads"))
        c.commit()
