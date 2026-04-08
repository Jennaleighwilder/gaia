"""Infrastructure inventory (culverts, guardrails, etc.) — waypoint-based."""

from __future__ import annotations

import csv
import io
from collections import Counter

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.road import Road
from backend.models.waypoint import Waypoint

router = APIRouter(prefix="/infrastructure", tags=["infrastructure"])

INFRA_TYPES = frozenset(
    {
        "culvert",
        "speed_limit",
        "guardrail",
        "bridge",
        "gate",
        "cattle_guard",
        "turnout",
    }
)


@router.get("/summary")
def infra_summary(db: Session = Depends(get_db)) -> dict:
    q = (
        select(Waypoint.waypoint_type, Waypoint.asset_condition, Waypoint.replacement_priority)
        .where(Waypoint.deleted_at.is_(None))
        .where(Waypoint.waypoint_type.in_(INFRA_TYPES))
    )
    rows = db.execute(q).all()
    by_type = Counter()
    by_cond = Counter()
    urgent = 0
    for typ, cond, pri in rows:
        if typ:
            by_type[typ] += 1
        if cond:
            by_cond[cond] += 1
        if pri in ("high", "urgent"):
            urgent += 1
    return {
        "count_by_type": dict(by_type),
        "count_by_condition": dict(by_cond),
        "high_priority_count": urgent,
        "total": len(rows),
    }


@router.get("/export/csv")
def infra_export_csv(db: Session = Depends(get_db)) -> StreamingResponse:
    q = (
        select(Waypoint, Road.road_name)
        .outerjoin(Road, Waypoint.road_id == Road.id)
        .where(Waypoint.deleted_at.is_(None))
        .where(Waypoint.waypoint_type.in_(INFRA_TYPES))
        .order_by(Waypoint.id)
    )
    rows = db.execute(q).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "id",
            "road_id",
            "road_name",
            "waypoint_type",
            "label",
            "lat",
            "lon",
            "asset_condition",
            "asset_notes",
            "last_inspected",
            "inspected_by",
            "replacement_priority",
        ]
    )
    for wp, rname in rows:
        w.writerow(
            [
                wp.id,
                wp.road_id,
                rname or "",
                wp.waypoint_type or "",
                wp.label or "",
                float(wp.lat) if wp.lat is not None else "",
                float(wp.lon) if wp.lon is not None else "",
                wp.asset_condition or "",
                (wp.asset_notes or "").replace("\n", " ")[:500],
                wp.last_inspected.isoformat() if wp.last_inspected else "",
                wp.inspected_by or "",
                wp.replacement_priority or "",
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="ferry_infrastructure.csv"'},
    )
