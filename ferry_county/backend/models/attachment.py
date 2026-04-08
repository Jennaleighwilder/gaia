from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    sha256_hex: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(
        String(48),
        nullable=False,
        index=True,
    )  # invoice | photo | match_backup | davis_bacon_wage | buy_america_cert | export_manifest | other
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)

    treatment_id: Mapped[int | None] = mapped_column(ForeignKey("treatments.id"), nullable=True, index=True)
    waypoint_id: Mapped[int | None] = mapped_column(ForeignKey("waypoints.id"), nullable=True, index=True)
    quarterly_financial_report_id: Mapped[int | None] = mapped_column(
        ForeignKey("quarterly_financial_reports.id"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
