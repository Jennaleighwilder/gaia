from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    road_id: Mapped[int | None] = mapped_column(ForeignKey("roads.id"), nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_gps: Mapped[object | None] = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    end_gps: Mapped[object | None] = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    track_line: Mapped[object | None] = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326), nullable=True)
    calculated_miles: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    raw_gps_log: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
