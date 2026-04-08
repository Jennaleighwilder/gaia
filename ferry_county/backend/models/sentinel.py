from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SentinelScan(Base):
    __tablename__ = "sentinel_scans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scan_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atmosphere_fwi: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    atmosphere_rh: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    atmosphere_wind: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    red_flag_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    palmer_drought: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    soil_moisture: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    scan_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    road_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SentinelRoadRisk(Base):
    __tablename__ = "sentinel_road_risks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("sentinel_scans.id"), nullable=False, index=True)
    road_id: Mapped[int] = mapped_column(ForeignKey("roads.id"), nullable=False, index=True)
    risk_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    convergence_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    atmosphere_contributing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    canopy_contributing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ground_contributing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    primary_driver: Mapped[str | None] = mapped_column(String(20), nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
