from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.models.audit import AuditLog


def write_audit(
    db: Session,
    *,
    table_name: str,
    record_id: int | None,
    action: str,
    actor: str | None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    detail: str | None = None,
) -> None:
    row = AuditLog(
        table_name=table_name,
        record_id=record_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        actor=actor,
        detail=detail,
    )
    db.add(row)
