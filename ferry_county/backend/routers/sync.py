from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.api import SyncOperationIn
from backend.services.sync_service import (
    SyncPayloadConflict,
    SyncUnsupportedOperation,
    apply_idempotent_operation,
)

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/operations")
def post_operation(
    body: SyncOperationIn,
    db: Session = Depends(get_db),
    x_actor: str | None = Header(default=None, alias="X-Actor"),
) -> dict:
    actor = x_actor or (body.payload.get("actor") if isinstance(body.payload, dict) else None)
    try:
        return apply_idempotent_operation(
            db,
            client_operation_id=body.client_operation_id,
            entity_type=body.entity_type,
            operation=body.operation,
            payload=body.payload,
            actor=actor,
        )
    except SyncPayloadConflict as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except SyncUnsupportedOperation as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
