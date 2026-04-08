from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.public_portal import EvacuationZone, PublicIncident, RoadClosure
from backend.models.road import Road


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def public_last_updated(db: Session) -> datetime:
    """Latest change time across public-facing rows."""
    ts: list[datetime] = []
    for mx in (
        db.scalar(select(func.max(EvacuationZone.created_at))),
        db.scalar(select(func.max(RoadClosure.closed_at))),
        db.scalar(select(func.max(PublicIncident.reported_at))),
    ):
        if mx is not None:
            ts.append(mx)
    if not ts:
        return _utc_now()
    return max(ts)


def evacuation_zones_geojson(db: Session) -> dict[str, Any]:
    q = select(
        EvacuationZone.id,
        EvacuationZone.zone_name,
        EvacuationZone.level,
        EvacuationZone.description,
        EvacuationZone.activated_at,
        func.ST_AsGeoJSON(EvacuationZone.geometry, 6).label("geom"),
    ).where(EvacuationZone.active.is_(True))
    feats = []
    for zid, name, level, desc, act_at, gj in db.execute(q).all():
        feats.append(
            {
                "type": "Feature",
                "id": zid,
                "properties": {
                    "zone_name": name,
                    "level": level,
                    "description": desc,
                    "activated_at": act_at.isoformat() if act_at else None,
                },
                "geometry": json.loads(gj) if gj else None,
            }
        )
    return {"type": "FeatureCollection", "features": feats}


def incidents_geojson(db: Session) -> dict[str, Any]:
    q = select(
        PublicIncident.id,
        PublicIncident.incident_type,
        PublicIncident.title,
        PublicIncident.description,
        PublicIncident.severity,
        PublicIncident.reported_at,
        func.ST_AsGeoJSON(PublicIncident.location, 6).label("geom"),
    ).where(PublicIncident.active.is_(True))
    feats = []
    for iid, typ, title, desc, sev, rep, gj in db.execute(q).all():
        feats.append(
            {
                "type": "Feature",
                "id": iid,
                "properties": {
                    "incident_type": typ,
                    "title": title,
                    "description": desc,
                    "severity": sev,
                    "reported_at": rep.isoformat() if rep else None,
                },
                "geometry": json.loads(gj) if gj else None,
            }
        )
    return {"type": "FeatureCollection", "features": feats}


def road_closures_public(db: Session) -> list[dict[str, Any]]:
    q = (
        select(
            RoadClosure,
            Road.road_name,
            Road.road_number,
            func.ST_AsGeoJSON(Road.geometry, 6).label("road_geom"),
            func.ST_AsGeoJSON(RoadClosure.detour_route, 6).label("detour_geom"),
        )
        .join(Road, RoadClosure.road_id == Road.id)
        .where(RoadClosure.active.is_(True))
        .where(Road.deleted_at.is_(None))
    )
    out = []
    for rc, rname, rnum, rgj, dgj in db.execute(q).all():
        out.append(
            {
                "id": rc.id,
                "road_id": rc.road_id,
                "road_name": rname,
                "road_number": rnum,
                "closure_reason": rc.closure_reason,
                "closure_type": rc.closure_type,
                "status": rc.status,
                "closed_at": rc.closed_at.isoformat() if rc.closed_at else None,
                "estimated_reopen": rc.estimated_reopen.isoformat() if rc.estimated_reopen else None,
                "detour_notes": rc.detour_notes,
                "road_geometry": json.loads(rgj) if rgj else None,
                "detour_route": json.loads(dgj) if dgj else None,
            }
        )
    return out


def public_status_bundle(db: Session) -> dict[str, Any]:
    zones = evacuation_zones_geojson(db)
    closures = road_closures_public(db)
    incidents = incidents_geojson(db)
    active_evac = [f for f in zones["features"] if f["properties"].get("level", 0) >= 2]
    return {
        "last_updated": public_last_updated(db).isoformat(),
        "active_evacuation_zones": active_evac,
        "road_closure_count": len(closures),
        "active_incident_count": len(incidents["features"]),
        "evacuation_zone_count": len(zones["features"]),
        "road_closures_summary": [
            {
                "id": c["id"],
                "road_name": c["road_name"],
                "status": c["status"],
                "closure_type": c["closure_type"],
            }
            for c in closures
        ],
        "incidents_summary": [
            {
                "id": f["id"],
                "title": f["properties"].get("title"),
                "incident_type": f["properties"].get("incident_type"),
                "severity": f["properties"].get("severity"),
            }
            for f in incidents["features"]
        ],
    }
