from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from geoalchemy2.functions import ST_Centroid, ST_X, ST_Y
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


@router.get("/search")
def search_roads(
    q: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
) -> dict:
    """Live road name search for Field map (ILIKE, max 10). Requires non-empty q after trim."""
    if q is None:
        raise HTTPException(status_code=400, detail="q required")
    qq = q.strip()
    if not qq:
        raise HTTPException(status_code=400, detail="q required")
    pat = f"%{qq}%"
    stmt = (
        select(
            Road.id,
            Road.road_name,
            Road.road_number,
            Road.cemp_miles,
            ST_Y(ST_Centroid(Road.geometry)).label("center_lat"),
            ST_X(ST_Centroid(Road.geometry)).label("center_lon"),
        )
        .where(Road.deleted_at.is_(None))
        .where(Road.road_name.ilike(pat))
        .order_by(Road.road_name)
        .limit(10)
    )
    rows = db.execute(stmt).all()
    items = []
    for r in rows:
        lat = float(r.center_lat) if r.center_lat is not None else None
        lon = float(r.center_lon) if r.center_lon is not None else None
        cemp = float(r.cemp_miles) if r.cemp_miles is not None else None
        items.append(
            {
                "id": r.id,
                "road_name": r.road_name,
                "road_number": r.road_number,
                "cemp_miles": cemp,
                "center_lat": lat,
                "center_lon": lon,
            }
        )
    return {"items": items}


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
