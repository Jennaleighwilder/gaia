#!/usr/bin/env python3
"""
Smoke the full spine without uvicorn: PostGIS → KMZ bytes import → treatment → reimbursement JSON.

Usage:
  export DATABASE_URL=postgresql+psycopg2://ferry:ferry@127.0.0.1:5434/ferry
  export FERRY_KMZ=/path/to/FerryCounty_Complete_Roads_v2.kmz
  python scripts/vertical_slice.py

Or pass path as argv[1]. Requires Docker (`docker-compose up -d`) and `alembic upgrade head` first.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

# Repo root = parent of scripts/
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select, text  # noqa: E402

from backend.config import reset_settings_cache  # noqa: E402
from backend.database import Base, get_engine, get_session_factory, reset_engine  # noqa: E402
import backend.models  # noqa: F401, E402
from backend.models.road import Road  # noqa: E402
from backend.services.compliance_engine import reimbursement_record  # noqa: E402
from backend.services.gis_export import roads_geojson  # noqa: E402
from backend.services.seed_kmz import import_kmz_upload  # noqa: E402
from backend.services.treatment_service import create_treatment  # noqa: E402


def main() -> int:
    kmz = os.environ.get("FERRY_KMZ") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not kmz:
        print("Set FERRY_KMZ or pass path to FerryCounty_Complete_Roads_v2.kmz", file=sys.stderr)
        return 2
    p = Path(kmz)
    if not p.is_file():
        print(f"KMZ not found: {p}", file=sys.stderr)
        return 2

    reset_settings_cache()
    reset_engine()
    eng = get_engine()
    with eng.connect() as c:
        c.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        c.commit()
    Base.metadata.create_all(bind=eng)

    data = p.read_bytes()
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        stats = import_kmz_upload(db, data, actor="vertical-slice")
        print("IMPORT", json.dumps(stats, indent=2))
        rid = db.execute(select(Road.id).order_by(Road.id).limit(1)).scalar_one_or_none()
        if rid is None:
            print("No roads after import", file=sys.stderr)
            return 1
        t = create_treatment(
            db,
            road_id=rid,
            treatment_date=date(2026, 4, 8),
            miles_treated=0.01,
            treatment_type="brush_clear",
            contractor="Vertical Slice Co",
            contractor_task_order="VS-1",
            contractor_invoice_amount=100.0,
            logged_by="script",
            match_documented=True,
            match_source="cash",
            match_amount=25.0,
            amount_federal=75.0,
            amount_match=25.0,
            davis_bacon_certified=True,
            davis_bacon_wage_rate=None,
            notes="automated smoke",
            actor="vertical-slice",
        )
        db.commit()
        rec = reimbursement_record(db, t.id)
        print("REIMBURSEMENT", json.dumps(rec, indent=2, default=str))
        gj = roads_geojson(db, treated_only=False)
        print("GEOJSON_FEATURES", len(gj.get("features", [])))
    finally:
        db.close()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
