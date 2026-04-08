from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.track import Track
from backend.schemas.api import TrackCreate
from backend.services.track_service import create_track

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.post("")
def post_track(
    body: TrackCreate,
    db: Session = Depends(get_db),
    x_actor: str | None = Header(default=None, alias="X-Actor"),
) -> dict:
    try:
        pts = [p.model_dump() for p in body.points]
        t = create_track(
            db,
            road_id=body.road_id,
            points=pts,
            start_time=body.start_time,
            end_time=body.end_time,
            actor=x_actor or "field",
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {
        "id": t.id,
        "road_id": t.road_id,
        "calculated_miles": float(t.calculated_miles) if t.calculated_miles is not None else None,
        "vertex_count": len(body.points),
    }


@router.get("/{track_id}")
def get_track(track_id: int, db: Session = Depends(get_db)) -> dict:
    t = db.get(Track, track_id)
    if t is None:
        raise HTTPException(404, "track not found")
    raw = t.raw_gps_log or {}
    return {
        "id": t.id,
        "road_id": t.road_id,
        "calculated_miles": float(t.calculated_miles) if t.calculated_miles is not None else None,
        "start_time": t.start_time.isoformat() if t.start_time else None,
        "end_time": t.end_time.isoformat() if t.end_time else None,
        "raw_gps_log": raw,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "created_by": t.created_by,
    }


@router.get("")
def list_tracks(
    db: Session = Depends(get_db),
    road_id: int | None = None,
    limit: int = Query(default=25, ge=1, le=200),
) -> dict:
    q = select(Track).order_by(Track.id.desc())
    if road_id is not None:
        q = q.where(Track.road_id == road_id)
    rows = db.execute(q.limit(limit)).scalars().all()
    items = []
    for t in rows:
        raw = t.raw_gps_log or {}
        n = raw.get("vertex_count") or len(raw.get("points") or [])
        items.append(
            {
                "id": t.id,
                "road_id": t.road_id,
                "calculated_miles": float(t.calculated_miles) if t.calculated_miles is not None else None,
                "vertex_count": n,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
        )
    return {"items": items}
