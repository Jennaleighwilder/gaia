from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class EvacuationZone(Base):
    __tablename__ = "evacuation_zones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    zone_name: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    geometry: Mapped[object] = mapped_column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RoadClosure(Base):
    __tablename__ = "road_closures"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    road_id: Mapped[int] = mapped_column(ForeignKey("roads.id"), nullable=False)
    closure_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    closure_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    detour_route: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326), nullable=True
    )
    detour_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estimated_reopen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # public display: closed = red, caution = orange (maps to closure_type or separate flag)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="closed")  # closed | caution | open


class PublicIncident(Base):
    __tablename__ = "public_incidents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    incident_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[object] = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="moderate")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reported_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
