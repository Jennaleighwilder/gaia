from __future__ import annotations

from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Waypoint(Base):
    __tablename__ = "waypoints"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    road_id: Mapped[int | None] = mapped_column(ForeignKey("roads.id"), nullable=True)
    waypoint_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[float | None] = mapped_column(Numeric(11, 7), nullable=True)
    lon: Mapped[float | None] = mapped_column(Numeric(11, 7), nullable=True)
    geometry: Mapped[object | None] = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)

    buy_america_certified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    material_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(160), nullable=True)

    asset_condition: Mapped[str | None] = mapped_column(String(20), nullable=True)
    asset_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_inspected: Mapped[date | None] = mapped_column(Date, nullable=True)
    inspected_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    replacement_priority: Mapped[str | None] = mapped_column(String(10), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
