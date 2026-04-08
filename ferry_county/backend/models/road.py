from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Road(Base):
    __tablename__ = "roads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_feature_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    road_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    road_name: Mapped[str] = mapped_column(String(200), nullable=False)
    district: Mapped[int | None] = mapped_column(Integer, nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(80), nullable=True)
    federal_class: Mapped[str | None] = mapped_column(String(80), nullable=True)
    length_mi: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    cemp_miles: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    cbmp_miles: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    begin_point: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    end_point: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    treatment_status: Mapped[str] = mapped_column(String(32), nullable=False, default="untreated")
    geometry: Mapped[object] = mapped_column(Geometry(geometry_type="MULTILINESTRING", srid=4326))
    kml_folder_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
