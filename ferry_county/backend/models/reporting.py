from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class QuarterlyFinancialReport(Base):
    __tablename__ = "quarterly_financial_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    quarter: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    federal_spend: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    match_cash: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    match_inkind: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    total_spend: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    match_ratio: Mapped[float | None] = mapped_column(Numeric(7, 4), nullable=True)
    submitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    submitted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AnnualPerformanceReport(Base):
    __tablename__ = "annual_performance_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    miles_treated: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    acres_treated: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    segments_treated: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pct_complete: Mapped[float | None] = mapped_column(Numeric(7, 4), nullable=True)
    signs_installed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mile_markers_installed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spatial_export_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    submitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    submitted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ReportingObligation(Base):
    """Configurable reporting calendar — do not hardcode cadence in code."""

    __tablename__ = "reporting_obligations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    obligation_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    period_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
