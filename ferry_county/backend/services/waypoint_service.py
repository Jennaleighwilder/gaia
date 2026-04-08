from __future__ import annotations

from datetime import datetime

from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session

from backend.models.road import Road
from backend.models.waypoint import Waypoint
from backend.services.audit_service import write_audit


def create_waypoint(
    db: Session,
    *,
    road_id: int | None,
    lat: float,
    lon: float,
    waypoint_type: str | None,
    label: str | None,
    notes: str | None,
    buy_america_certified: bool,
    material_cost: float | None,
    vendor: str | None,
    actor: str | None,
    asset_condition: str | None = None,
    asset_notes: str | None = None,
    last_inspected: object | None = None,
    inspected_by: str | None = None,
    replacement_priority: str | None = None,
) -> Waypoint:
    if road_id is not None and db.get(Road, road_id) is None:
        raise ValueError("road not found")
    geom = WKTElement(f"POINT({lon} {lat})", 4326)
    w = Waypoint(
        road_id=road_id,
        waypoint_type=waypoint_type,
        label=label,
        notes=notes,
        lat=lat,
        lon=lon,
        geometry=geom,
        buy_america_certified=buy_america_certified,
        material_cost=material_cost,
        vendor=vendor,
        asset_condition=asset_condition,
        asset_notes=asset_notes,
        last_inspected=last_inspected,
        inspected_by=inspected_by,
        replacement_priority=replacement_priority,
        created_by=actor,
        updated_by=actor,
        updated_at=datetime.utcnow(),
    )
    db.add(w)
    db.flush()
    write_audit(
        db,
        table_name="waypoints",
        record_id=w.id,
        action="create",
        actor=actor,
        new_value={"road_id": road_id, "label": label, "waypoint_type": waypoint_type},
    )
    return w
