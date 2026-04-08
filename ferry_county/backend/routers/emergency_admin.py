"""Steve / EOC writes for public portal (trusted header actor — same pattern as field app)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from geoalchemy2.elements import WKTElement
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.public_portal import EvacuationZone, PublicIncident, RoadClosure
from backend.models.road import Road

router = APIRouter(prefix="/emergency", tags=["emergency"])


class EvacZoneBody(BaseModel):
    zone_name: str = Field(max_length=100)
    level: int = Field(ge=1, le=3)
    description: str | None = None
    wkt_polygon: str = Field(description="WKT POLYGON in EPSG:4326")


class EvacPatch(BaseModel):
    active: bool
    level: int | None = Field(default=None, ge=1, le=3)


class RoadCloseBody(BaseModel):
    road_id: int
    closure_reason: str | None = None
    closure_type: str | None = Field(default="other", max_length=30)
    detour_wkt: str | None = None
    detour_notes: str | None = None
    estimated_reopen_iso: str | None = None
    status: str = Field(default="closed", max_length=20)


class IncidentBody(BaseModel):
    incident_type: str = Field(max_length=30)
    title: str = Field(max_length=200)
    description: str | None = None
    lat: float
    lon: float
    severity: str = Field(default="moderate", max_length=20)


@router.get("/evacuation-zones")
def list_zones(db: Session = Depends(get_db)) -> dict:
    rows = db.execute(select(EvacuationZone).order_by(EvacuationZone.id.desc()).limit(500)).scalars().all()
    return {
        "items": [
            {
                "id": z.id,
                "zone_name": z.zone_name,
                "level": z.level,
                "active": z.active,
                "activated_at": z.activated_at.isoformat() if z.activated_at else None,
            }
            for z in rows
        ]
    }


@router.post("/evacuation-zones")
def create_zone(
    body: EvacZoneBody,
    db: Session = Depends(get_db),
    x_actor: str | None = Header(default=None, alias="X-Actor"),
) -> dict:
    actor = x_actor or "eoc"
    z = EvacuationZone(
        zone_name=body.zone_name,
        level=body.level,
        description=body.description,
        geometry=WKTElement(body.wkt_polygon, 4326),
        active=True,
        activated_at=datetime.now(timezone.utc),
        activated_by=actor,
    )
    db.add(z)
    db.commit()
    db.refresh(z)
    return {"id": z.id}


@router.patch("/evacuation-zones/{zone_id}")
def patch_zone(
    zone_id: int,
    body: EvacPatch,
    db: Session = Depends(get_db),
    x_actor: str | None = Header(default=None, alias="X-Actor"),
) -> dict:
    z = db.get(EvacuationZone, zone_id)
    if z is None:
        raise HTTPException(404, "zone not found")
    z.active = body.active
    if body.level is not None:
        z.level = body.level
    z.activated_by = x_actor or z.activated_by
    if body.active:
        z.activated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.post("/road-closures")
def close_road(
    body: RoadCloseBody,
    db: Session = Depends(get_db),
    x_actor: str | None = Header(default=None, alias="X-Actor"),
) -> dict:
    if db.get(Road, body.road_id) is None:
        raise HTTPException(400, "road not found")
    geom = None
    if body.detour_wkt:
        geom = WKTElement(body.detour_wkt, 4326)
    est = None
    if body.estimated_reopen_iso:
        try:
            est = datetime.fromisoformat(body.estimated_reopen_iso.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(400, "bad estimated_reopen_iso") from None
    rc = RoadClosure(
        road_id=body.road_id,
        closure_reason=body.closure_reason,
        closure_type=body.closure_type,
        detour_route=geom,
        detour_notes=body.detour_notes,
        closed_by=x_actor or "eoc",
        estimated_reopen=est,
        active=True,
        status=body.status,
    )
    db.add(rc)
    db.commit()
    db.refresh(rc)
    return {"id": rc.id}


@router.patch("/road-closures/{closure_id}/resolve")
def resolve_closure(
    closure_id: int,
    db: Session = Depends(get_db),
) -> dict:
    rc = db.get(RoadClosure, closure_id)
    if rc is None:
        raise HTTPException(404, "closure not found")
    rc.active = False
    rc.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.post("/incidents")
def post_incident(
    body: IncidentBody,
    db: Session = Depends(get_db),
    x_actor: str | None = Header(default=None, alias="X-Actor"),
) -> dict:
    pt = WKTElement(f"POINT({body.lon} {body.lat})", 4326)
    inc = PublicIncident(
        incident_type=body.incident_type,
        title=body.title,
        description=body.description,
        location=pt,
        severity=body.severity,
        active=True,
        reported_by=x_actor or "eoc",
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)
    return {"id": inc.id}


@router.patch("/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: int, db: Session = Depends(get_db)) -> dict:
    inc = db.get(PublicIncident, incident_id)
    if inc is None:
        raise HTTPException(404, "incident not found")
    inc.active = False
    inc.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.get("/roads-search")
def roads_search(q: str, db: Session = Depends(get_db), limit: int = 20) -> dict:
    qq = f"%{q.strip()}%"
    rows = db.execute(
        select(Road)
        .where(Road.deleted_at.is_(None))
        .where(Road.road_name.ilike(qq))
        .order_by(Road.road_name)
        .limit(limit)
    ).scalars().all()
    return {
        "items": [
            {"id": r.id, "road_name": r.road_name, "road_number": r.road_number} for r in rows
        ]
    }