from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class TreatmentCreate(BaseModel):
    treatment_date: date
    miles_treated: float = Field(gt=0)
    treatment_type: str | None = None
    contractor: str | None = None
    contractor_task_order: str | None = None
    contractor_invoice_amount: float | None = None
    logged_by: str | None = None
    match_documented: bool = False
    match_source: str | None = None
    match_amount: float | None = None
    amount_federal: float | None = None
    amount_match: float | None = None
    davis_bacon_certified: bool = False
    davis_bacon_wage_rate: float | None = None
    notes: str | None = None
    track_id: int | None = Field(default=None, description="Optional field GPS track evidence row")
    client_track_operation_id: str | None = Field(
        default=None,
        min_length=32,
        max_length=36,
        description="If track not yet assigned an id, reference the track's sync client_operation_id (server resolves).",
    )

    @field_validator("client_track_operation_id", mode="before")
    @classmethod
    def _normalize_client_track_op(cls, v: object) -> object:
        if v == "":
            return None
        return v


class GpsPointIn(BaseModel):
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    accuracy_m: float | None = Field(default=None, ge=0)


class TrackCreate(BaseModel):
    """Recorded field track (vertices along a treatment path)."""

    road_id: int | None = Field(default=None, description="Optional association; may be set later on treatment")
    points: list[GpsPointIn] = Field(min_length=2)
    start_time: datetime | None = None
    end_time: datetime | None = None


class ImportKmzBody(BaseModel):
    kmz_path: str


class TreatmentSyncPayload(TreatmentCreate):
    """Treatment create via /sync/operations — includes road_id (flat JSON for field clients)."""

    road_id: int = Field(gt=0)
    actor: str | None = Field(default=None, description="Fallback if X-Actor header missing")


class TrackSyncPayload(TrackCreate):
    """Track create via /sync/operations — same fields as REST body."""

    actor: str | None = Field(default=None, description="Fallback if X-Actor header missing")


class WaypointCreate(BaseModel):
    road_id: int | None = None
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    waypoint_type: str | None = Field(default=None, max_length=40)
    label: str | None = Field(default=None, max_length=200)
    notes: str | None = None
    buy_america_certified: bool = False
    material_cost: float | None = Field(default=None, ge=0)
    vendor: str | None = Field(default=None, max_length=160)
    asset_condition: str | None = Field(default=None, max_length=20)
    asset_notes: str | None = None
    last_inspected: date | None = None
    inspected_by: str | None = Field(default=None, max_length=100)
    replacement_priority: str | None = Field(default=None, max_length=10)


class WaypointSyncPayload(WaypointCreate):
    actor: str | None = Field(default=None, description="Fallback if X-Actor header missing")


class QuarterlyReportCreate(BaseModel):
    """Quarterly financial submission — match ratio derived from federal + match totals."""

    quarter: str = Field(min_length=3, max_length=16, description='e.g. "2026-Q1"')
    federal_spend: float | None = Field(default=None, ge=0)
    match_cash: float | None = Field(default=None, ge=0)
    match_inkind: float | None = Field(default=None, ge=0)
    submitted: bool = False
    submitted_date: date | None = None
    notes: str | None = None


class SyncOperationIn(BaseModel):
    client_operation_id: str = Field(min_length=32, max_length=36)
    entity_type: str
    operation: str
    payload: dict
