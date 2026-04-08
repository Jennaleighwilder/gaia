from __future__ import annotations

from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Treatment(Base):
    __tablename__ = "treatments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    road_id: Mapped[int] = mapped_column(ForeignKey("roads.id"), nullable=False)
    treatment_date: Mapped[date] = mapped_column(Date, nullable=False)
    miles_treated: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    acres_treated: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    treatment_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    contractor: Mapped[str | None] = mapped_column(String(160), nullable=True)
    contractor_task_order: Mapped[str | None] = mapped_column(String(80), nullable=True)
    contractor_invoice_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    logged_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    gps_start: Mapped[object | None] = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    gps_end: Mapped[object | None] = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    track_id: Mapped[int | None] = mapped_column(ForeignKey("tracks.id"), nullable=True)

    match_documented: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    match_source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    match_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    amount_federal: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    amount_match: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)

    davis_bacon_certified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    davis_bacon_wage_rate: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    submitted_to_usda: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    submission_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
