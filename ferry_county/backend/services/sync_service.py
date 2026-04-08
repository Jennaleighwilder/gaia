from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models.sync import ReconciliationLog, SyncOperation
from backend.schemas.api import TrackSyncPayload, TreatmentSyncPayload, WaypointSyncPayload
from backend.services.treatment_service import create_treatment
from backend.services.track_service import create_track
from backend.services.waypoint_service import create_waypoint


class SyncPayloadConflict(Exception):
    """Same client_operation_id replayed with a different payload (hash mismatch)."""

    def __init__(self, message: str = "client_operation_id already used with different payload"):
        super().__init__(message)


class SyncUnsupportedOperation(Exception):
    def __init__(self, entity_type: str, operation: str):
        super().__init__(f"unsupported sync operation: {entity_type}/{operation}")
        self.entity_type = entity_type
        self.operation = operation


def _payload_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _pg_advisory_lock_client_op(db: Session, client_operation_id: str) -> None:
    """Serialize sync replays for the same client_operation_id (PostgreSQL only)."""
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    b = hashlib.sha256(client_operation_id.encode()).digest()
    k1 = int.from_bytes(b[:4], "big") & 0x7FFFFFFF
    k2 = int.from_bytes(b[4:8], "big") & 0x7FFFFFFF
    db.execute(text("SELECT pg_advisory_xact_lock(:a, :b)"), {"a": k1, "b": k2})


def _build_response(
    *,
    status: str,
    sync_operation_id: int,
    payload_hash: str,
    result: dict | None,
) -> dict:
    out: dict = {
        "status": status,
        "sync_operation_id": sync_operation_id,
        "payload_hash": payload_hash,
    }
    if result is not None:
        out["result"] = result
    return out


def _dispatch_apply(
    db: Session,
    *,
    entity_type: str,
    operation: str,
    payload: dict,
    actor: str | None,
) -> dict:
    et = entity_type.strip().lower()
    op = operation.strip().lower()
    if et == "treatment" and op == "create":
        data = TreatmentSyncPayload.model_validate(payload)
        act = actor or data.actor or "sync"
        t = create_treatment(
            db,
            road_id=data.road_id,
            treatment_date=data.treatment_date,
            miles_treated=data.miles_treated,
            treatment_type=data.treatment_type,
            contractor=data.contractor,
            contractor_task_order=data.contractor_task_order,
            contractor_invoice_amount=data.contractor_invoice_amount,
            logged_by=data.logged_by,
            match_documented=data.match_documented,
            match_source=data.match_source,
            match_amount=data.match_amount,
            amount_federal=data.amount_federal,
            amount_match=data.amount_match,
            davis_bacon_certified=data.davis_bacon_certified,
            davis_bacon_wage_rate=data.davis_bacon_wage_rate,
            notes=data.notes,
            actor=act,
            track_id=data.track_id,
            client_track_operation_id=data.client_track_operation_id,
        )
        db.flush()
        return {"entity": "treatment", "treatment_id": t.id, "road_id": data.road_id}
    if et == "track" and op == "create":
        data = TrackSyncPayload.model_validate(payload)
        act = actor or data.actor or "sync"
        pts = [p.model_dump() for p in data.points]
        tr = create_track(
            db,
            road_id=data.road_id,
            points=pts,
            start_time=data.start_time,
            end_time=data.end_time,
            actor=act,
        )
        db.flush()
        return {"entity": "track", "track_id": tr.id, "road_id": data.road_id}
    if et == "waypoint" and op == "create":
        data = WaypointSyncPayload.model_validate(payload)
        act = actor or data.actor or "sync"
        w = create_waypoint(
            db,
            road_id=data.road_id,
            lat=data.lat,
            lon=data.lon,
            waypoint_type=data.waypoint_type,
            label=data.label,
            notes=data.notes,
            buy_america_certified=data.buy_america_certified,
            material_cost=data.material_cost,
            vendor=data.vendor,
            actor=act,
            asset_condition=data.asset_condition,
            asset_notes=data.asset_notes,
            last_inspected=data.last_inspected,
            inspected_by=data.inspected_by,
            replacement_priority=data.replacement_priority,
        )
        db.flush()
        return {"entity": "waypoint", "waypoint_id": w.id, "road_id": data.road_id}
    raise SyncUnsupportedOperation(entity_type, operation)


def apply_idempotent_operation(
    db: Session,
    *,
    client_operation_id: str,
    entity_type: str,
    operation: str,
    payload: dict,
    actor: str | None = None,
) -> dict:
    """
    Apply a sync operation once. Same client_operation_id + identical payload → duplicate replay
    with stored result_json. Same id + different payload → SyncPayloadConflict (409).

    PostgreSQL: advisory lock prevents two concurrent "first applies" from double-creating rows.
    """
    h = _payload_hash(payload)
    _pg_advisory_lock_client_op(db, client_operation_id)

    existing = db.execute(
        select(SyncOperation).where(SyncOperation.client_operation_id == client_operation_id)
    ).scalar_one_or_none()

    if existing is not None:
        if existing.payload_hash != h:
            raise SyncPayloadConflict()
        db.add(
            ReconciliationLog(
                sync_operation_id=existing.id,
                detail={"event": "duplicate_client_operation_id", "replay": True},
            )
        )
        db.commit()
        return _build_response(
            status="duplicate",
            sync_operation_id=existing.id,
            payload_hash=existing.payload_hash,
            result=existing.result_json,
        )

    try:
        result = _dispatch_apply(db, entity_type=entity_type, operation=operation, payload=payload, actor=actor)
        op = SyncOperation(
            client_operation_id=client_operation_id,
            entity_type=entity_type,
            operation=operation,
            payload=payload,
            payload_hash=h,
            result_json=result,
            status="applied",
            applied_at=datetime.utcnow(),
        )
        db.add(op)
        db.flush()
        db.add(ReconciliationLog(sync_operation_id=op.id, detail={"event": "applied", "entity": result.get("entity")}))
        db.commit()
        return _build_response(status="applied", sync_operation_id=op.id, payload_hash=h, result=result)
    except IntegrityError:
        db.rollback()
        db.expire_all()
        existing2 = db.execute(
            select(SyncOperation).where(SyncOperation.client_operation_id == client_operation_id)
        ).scalar_one_or_none()
        if existing2 is None:
            raise
        if existing2.payload_hash != h:
            raise SyncPayloadConflict() from None
        db.add(
            ReconciliationLog(
                sync_operation_id=existing2.id,
                detail={"event": "duplicate_after_race", "replay": True},
            )
        )
        db.commit()
        return _build_response(
            status="duplicate",
            sync_operation_id=existing2.id,
            payload_hash=existing2.payload_hash,
            result=existing2.result_json,
        )
    except Exception:
        db.rollback()
        raise
