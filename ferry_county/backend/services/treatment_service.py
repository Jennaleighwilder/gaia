from __future__ import annotations

from datetime import date, datetime

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.road import Road
from backend.models.sync import SyncOperation
from backend.models.track import Track
from backend.models.treatment import Treatment
from backend.services.acreage import calculate_acres
from backend.services.audit_service import write_audit


def _resolve_track_id_from_sync(db: Session, client_operation_id: str) -> int:
    cid = client_operation_id.strip()
    row = db.execute(select(SyncOperation).where(SyncOperation.client_operation_id == cid)).scalar_one_or_none()
    if row is None or not row.result_json:
        raise ValueError("no sync result for client_track_operation_id; sync the track before this treatment")
    rj = row.result_json
    if rj.get("entity") != "track":
        raise ValueError("client_track_operation_id does not reference a track sync")
    tid = rj.get("track_id")
    if tid is None:
        raise ValueError("track_id missing from track sync result")
    return int(tid)


def create_treatment(
    db: Session,
    *,
    road_id: int,
    treatment_date: date,
    miles_treated: float,
    treatment_type: str | None,
    contractor: str | None,
    contractor_task_order: str | None,
    contractor_invoice_amount: float | None,
    logged_by: str | None,
    match_documented: bool,
    match_source: str | None,
    match_amount: float | None,
    amount_federal: float | None,
    amount_match: float | None,
    davis_bacon_certified: bool,
    davis_bacon_wage_rate: float | None,
    notes: str | None,
    actor: str | None,
    track_id: int | None = None,
    client_track_operation_id: str | None = None,
) -> Treatment:
    road = db.get(Road, road_id)
    if road is None:
        raise ValueError("road not found")

    gps_start = None
    gps_end = None
    tid = track_id
    if tid is None and client_track_operation_id:
        tid = _resolve_track_id_from_sync(db, client_track_operation_id)
    if tid is not None:
        tr = db.get(Track, tid)
        if tr is None:
            raise ValueError("track not found")
        if tr.road_id is not None and tr.road_id != road_id:
            raise ValueError("track is associated with a different road")
        raw = tr.raw_gps_log or {}
        pts = raw.get("points") or []
        if len(pts) >= 1:
            a, b = pts[0], pts[-1]
            gps_start = WKTElement(f"POINT({a['lon']} {a['lat']})", 4326)
            gps_end = WKTElement(f"POINT({b['lon']} {b['lat']})", 4326)

    acres = calculate_acres(miles_treated)
    t = Treatment(
        road_id=road_id,
        treatment_date=treatment_date,
        miles_treated=miles_treated,
        acres_treated=acres,
        treatment_type=treatment_type,
        contractor=contractor,
        contractor_task_order=contractor_task_order,
        contractor_invoice_amount=contractor_invoice_amount,
        notes=notes,
        logged_by=logged_by,
        gps_start=gps_start,
        gps_end=gps_end,
        track_id=tid,
        match_documented=match_documented,
        match_source=match_source,
        match_amount=match_amount,
        amount_federal=amount_federal,
        amount_match=amount_match,
        davis_bacon_certified=davis_bacon_certified,
        davis_bacon_wage_rate=davis_bacon_wage_rate,
        created_by=actor,
        updated_by=actor,
        updated_at=datetime.utcnow(),
    )
    db.add(t)
    db.flush()

    cbmp = float(road.cbmp_miles or 0) + float(miles_treated)
    road.cbmp_miles = cbmp
    cemp = float(road.cemp_miles or 0)
    if cemp > 0 and cbmp + 1e-9 >= cemp:
        road.treatment_status = "complete"
    elif cbmp > 0:
        road.treatment_status = "partial"
    road.updated_at = datetime.utcnow()
    road.updated_by = actor

    write_audit(
        db,
        table_name="treatments",
        record_id=t.id,
        action="create",
        actor=actor,
        new_value={
            "road_id": road_id,
            "miles_treated": miles_treated,
            "treatment_date": str(treatment_date),
            "track_id": tid,
            "client_track_operation_id": bool(client_track_operation_id),
        },
    )
    return t
