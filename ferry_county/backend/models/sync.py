from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SyncOperation(Base):
    __tablename__ = "sync_operations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_operation_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="applied")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReconciliationLog(Base):
    __tablename__ = "reconciliation_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sync_operation_id: Mapped[int] = mapped_column(ForeignKey("sync_operations.id"), nullable=False, index=True)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
