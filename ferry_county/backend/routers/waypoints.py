from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.waypoint import Waypoint
from backend.schemas.api import WaypointCreate
from backend.services.waypoint_service import create_waypoint

router = APIRouter(prefix="/waypoints", tags=["waypoints"])


@router.post("")
def post_waypoint(
    body: WaypointCreate,
    db: Session = Depends(get_db),
    x_actor: str | None = Header(default=None, alias="X-Actor"),
) -> dict:
    try:
        w = create_waypoint(
            db,
            road_id=body.road_id,
            lat=body.lat,
            lon=body.lon,
            waypoint_type=body.waypoint_type,
            label=body.label,
            notes=body.notes,
            buy_america_certified=body.buy_america_certified,
            material_cost=body.material_cost,
            vendor=body.vendor,
            actor=x_actor or "field",
            asset_condition=body.asset_condition,
            asset_notes=body.asset_notes,
            last_inspected=body.last_inspected,
            inspected_by=body.inspected_by,
            replacement_priority=body.replacement_priority,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {
        "id": w.id,
        "road_id": w.road_id,
        "lat": float(w.lat) if w.lat is not None else None,
        "lon": float(w.lon) if w.lon is not None else None,
        "buy_america_certified": w.buy_america_certified,
        "material_cost": float(w.material_cost) if w.material_cost is not None else None,
        "vendor": w.vendor,
    }


@router.get("/{waypoint_id}")
def get_waypoint(waypoint_id: int, db: Session = Depends(get_db)) -> dict:
    w = db.get(Waypoint, waypoint_id)
    if w is None or w.deleted_at is not None:
        raise HTTPException(404, "waypoint not found")
    return {
        "id": w.id,
        "road_id": w.road_id,
        "waypoint_type": w.waypoint_type,
        "label": w.label,
        "notes": w.notes,
        "lat": float(w.lat) if w.lat is not None else None,
        "lon": float(w.lon) if w.lon is not None else None,
        "buy_america_certified": w.buy_america_certified,
        "material_cost": float(w.material_cost) if w.material_cost is not None else None,
        "vendor": w.vendor,
        "asset_condition": w.asset_condition,
        "asset_notes": w.asset_notes,
        "last_inspected": w.last_inspected.isoformat() if w.last_inspected else None,
        "inspected_by": w.inspected_by,
        "replacement_priority": w.replacement_priority,
    }


@router.get("")
def list_waypoints(
    db: Session = Depends(get_db),
    road_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    q = select(Waypoint).where(Waypoint.deleted_at.is_(None)).order_by(Waypoint.id.desc())
    if road_id is not None:
        q = q.where(Waypoint.road_id == road_id)
    rows = db.execute(q.limit(limit)).scalars().all()
    return {
        "items": [
            {
                "id": w.id,
                "road_id": w.road_id,
                "label": w.label,
                "waypoint_type": w.waypoint_type,
                "lat": float(w.lat) if w.lat is not None else None,
                "lon": float(w.lon) if w.lon is not None else None,
                "buy_america_certified": w.buy_america_certified,
                "material_cost": float(w.material_cost) if w.material_cost is not None else None,
                "vendor": w.vendor,
                "asset_condition": w.asset_condition,
                "asset_notes": w.asset_notes,
                "last_inspected": w.last_inspected.isoformat() if w.last_inspected else None,
                "inspected_by": w.inspected_by,
                "replacement_priority": w.replacement_priority,
            }
            for w in rows
        ]
    }
