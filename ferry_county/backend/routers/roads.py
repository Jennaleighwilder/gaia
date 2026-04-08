from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.road import Road
from backend.services.gis_export import roads_field_map_geojson

router = APIRouter(prefix="/roads", tags=["roads"])


@router.get("/geojson")
def roads_geojson_endpoint(db: Session = Depends(get_db)) -> JSONResponse:
    """FeatureCollection for Field map (treatment status + grant vs non-grant)."""
    return JSONResponse(roads_field_map_geojson(db))


@router.get("")
def list_roads(
    db: Session = Depends(get_db),
    district: int | None = None,
    limit: int = Query(100, le=5000),
    offset: int = 0,
) -> dict:
    q = select(Road).where(Road.deleted_at.is_(None))
    if district is not None:
        q = q.where(Road.district == district)
    q = q.order_by(Road.id).limit(limit).offset(offset)
    rows = db.execute(q).scalars().all()
    return {
        "items": [
            {
                "id": r.id,
                "source_feature_id": r.source_feature_id,
                "road_name": r.road_name,
                "road_number": r.road_number,
                "district": r.district,
                "treatment_status": r.treatment_status,
                "cemp_miles": float(r.cemp_miles) if r.cemp_miles is not None else None,
                "cbmp_miles": float(r.cbmp_miles) if r.cbmp_miles is not None else None,
            }
            for r in rows
        ]
    }


@router.get("/by-source/{source_feature_id}")
def get_by_source(source_feature_id: str, db: Session = Depends(get_db)) -> dict:
    r = db.execute(select(Road).where(Road.source_feature_id == source_feature_id)).scalar_one_or_none()
    if r is None:
        raise HTTPException(404, "road not found")
    return {
        "id": r.id,
        "source_feature_id": r.source_feature_id,
        "road_name": r.road_name,
        "road_number": r.road_number,
        "treatment_status": r.treatment_status,
    }
