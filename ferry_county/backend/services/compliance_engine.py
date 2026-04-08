from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models.road import Road
from backend.models.track import Track
from backend.models.treatment import Treatment
from backend.models.waypoint import Waypoint
from backend.services.acreage import calculate_acres


def format_match_ratio_response(
    federal_spend_total: float,
    match_documented_total: float,
    match_ratio_required: float,
) -> dict[str, Any]:
    """Aggregate match share = match / (federal + match); compliant if share >= required (e.g. 0.25)."""
    denom = federal_spend_total + match_documented_total
    ratio_percent: float | None
    compliant: bool
    if denom <= 0:
        ratio_percent = None
        compliant = False
    else:
        share = match_documented_total / denom
        ratio_percent = round(share * 100.0, 4)
        compliant = share >= match_ratio_required - 1e-9
    return {
        "federal_spend_total": federal_spend_total,
        "match_documented_total": match_documented_total,
        "ratio_percent": ratio_percent,
        "compliant": compliant,
        "match_ratio_required_percent": round(match_ratio_required * 100.0, 4),
    }


def match_ratio_summary(db: Session) -> dict[str, Any]:
    """
    Program-level totals: sum of amount_federal (all active treatments) and sum of amount_match
    where match_documented is true.
    """
    settings = get_settings()
    fed = db.execute(
        select(func.coalesce(func.sum(Treatment.amount_federal), 0)).where(Treatment.deleted_at.is_(None))
    ).scalar_one()
    match_doc = db.execute(
        select(func.coalesce(func.sum(Treatment.amount_match), 0))
        .where(Treatment.deleted_at.is_(None))
        .where(Treatment.match_documented.is_(True))
    ).scalar_one()
    return format_match_ratio_response(
        float(fed or 0),
        float(match_doc or 0),
        settings.match_ratio_required,
    )


@dataclass
class ComplianceFlags:
    davis_bacon_warning: bool
    match_ratio_ok: bool | None
    match_ratio: float | None
    buy_america_notes: str | None = None


def _ratio(fed: float | None, match: float | None) -> float | None:
    if fed is None or match is None:
        return None
    ff = float(fed)
    mm = float(match)
    if ff + mm == 0:
        return None
    return mm / (ff + mm)


def compliance_flags_for_treatment(t: Treatment) -> ComplianceFlags:
    settings = get_settings()
    warn = False
    amt = t.contractor_invoice_amount
    if amt is not None and float(amt) > settings.davis_bacon_threshold_usd and not t.davis_bacon_certified:
        warn = True
    r = _ratio(t.amount_federal, t.amount_match)
    ok: bool | None = None
    if r is not None:
        ok = r >= settings.match_ratio_required - 1e-9
    return ComplianceFlags(davis_bacon_warning=warn, match_ratio_ok=ok, match_ratio=r)


def reimbursement_record(db: Session, treatment_id: int) -> dict[str, Any]:
    t = db.get(Treatment, treatment_id)
    if t is None:
        raise ValueError("treatment not found")
    road = db.get(Road, t.road_id)
    flags = compliance_flags_for_treatment(t)
    return {
        "treatment_id": t.id,
        "road_source_feature_id": road.source_feature_id if road else None,
        "road_name": road.road_name if road else None,
        "road_number": road.road_number if road else None,
        "district": road.district if road else None,
        "treatment_date": str(t.treatment_date),
        "miles_treated": float(t.miles_treated) if t.miles_treated is not None else None,
        "acres_treated": float(t.acres_treated) if t.acres_treated is not None else None,
        "treatment_type": t.treatment_type,
        "contractor": t.contractor,
        "contractor_task_order": t.contractor_task_order,
        "contractor_invoice_amount": float(t.contractor_invoice_amount) if t.contractor_invoice_amount else None,
        "match_documented": t.match_documented,
        "match_source": t.match_source,
        "match_amount": float(t.match_amount) if t.match_amount else None,
        "amount_federal": float(t.amount_federal) if t.amount_federal else None,
        "amount_match": float(t.amount_match) if t.amount_match else None,
        "davis_bacon_certified": t.davis_bacon_certified,
        "davis_bacon_wage_rate": float(t.davis_bacon_wage_rate) if t.davis_bacon_wage_rate else None,
        "compliance_flags": {
            "davis_bacon_warning": flags.davis_bacon_warning,
            "match_ratio": flags.match_ratio,
            "match_ratio_ok": flags.match_ratio_ok,
        },
        "submitted_to_usda": t.submitted_to_usda,
        "submission_date": str(t.submission_date) if t.submission_date else None,
    }


def reimbursement_package(
    db: Session,
    *,
    period_start: date,
    period_end: date,
) -> list[dict[str, Any]]:
    q = (
        select(Treatment)
        .where(Treatment.treatment_date >= period_start)
        .where(Treatment.treatment_date <= period_end)
        .where(Treatment.deleted_at.is_(None))
        .order_by(Treatment.treatment_date, Treatment.id)
    )
    rows = db.execute(q).scalars().all()
    return [reimbursement_record(db, t.id) for t in rows]


def create_quarterly_financial_report(
    db: Session,
    *,
    quarter: str,
    federal_spend: float | None,
    match_cash: float | None,
    match_inkind: float | None,
    submitted: bool,
    submitted_date: date | None,
    notes: str | None,
) -> Any:
    from backend.models.reporting import QuarterlyFinancialReport

    fed = float(federal_spend or 0)
    mc = float(match_cash or 0)
    mi = float(match_inkind or 0)
    match_total = mc + mi
    total_spend = fed + match_total
    match_ratio = (match_total / total_spend) if total_spend > 0 else None

    row = QuarterlyFinancialReport(
        quarter=quarter.strip(),
        federal_spend=federal_spend,
        match_cash=match_cash,
        match_inkind=match_inkind,
        total_spend=total_spend,
        match_ratio=match_ratio,
        submitted=submitted,
        submitted_date=submitted_date,
        notes=notes,
    )
    db.add(row)
    db.flush()
    return row


def _treatments_in_period(db: Session, period_start: date, period_end: date) -> list[Treatment]:
    q = (
        select(Treatment)
        .where(Treatment.treatment_date >= period_start)
        .where(Treatment.treatment_date <= period_end)
        .where(Treatment.deleted_at.is_(None))
        .order_by(Treatment.treatment_date, Treatment.id)
    )
    return list(db.execute(q).scalars().all())


def generate_semi_annual_report(db: Session, period_start: date, period_end: date) -> dict[str, Any]:
    """
    Semi-annual performance summary for USFS-style templates: miles, acres, road status counts,
    period match ratio, treatment rows, waypoint sign/mile-marker counts, compliance tallies.
    """
    settings = get_settings()
    treatments = _treatments_in_period(db, period_start, period_end)

    if not treatments:
        return {
            "period_start": str(period_start),
            "period_end": str(period_end),
            "total_miles_treated": 0.0,
            "total_acres_treated": 0.0,
            "roads_completed_count": 0,
            "roads_partial_count": 0,
            "match_ratio": format_match_ratio_response(0.0, 0.0, settings.match_ratio_required),
            "treatments": [],
            "waypoints_summary": {"signs_placed": 0, "mile_markers_placed": 0},
            "compliance_flags": {"davis_bacon_missing_count": 0, "buy_america_missing_count": 0},
        }

    total_miles = sum(float(t.miles_treated) for t in treatments)
    total_acres = sum(
        float(t.acres_treated) if t.acres_treated is not None else calculate_acres(float(t.miles_treated))
        for t in treatments
    )

    fed = sum(float(t.amount_federal or 0) for t in treatments)
    match_doc = sum(float(t.amount_match or 0) for t in treatments if t.match_documented)
    match_ratio = format_match_ratio_response(fed, match_doc, settings.match_ratio_required)

    road_ids = {t.road_id for t in treatments}
    roads_completed = 0
    roads_partial = 0
    for rid in road_ids:
        road = db.get(Road, rid)
        if road is None:
            continue
        if road.treatment_status == "complete":
            roads_completed += 1
        elif road.treatment_status == "partial":
            roads_partial += 1

    treatment_rows: list[dict[str, Any]] = []
    davis_missing = 0
    for t in treatments:
        road = db.get(Road, t.road_id)
        acres = float(t.acres_treated) if t.acres_treated is not None else calculate_acres(float(t.miles_treated))
        flags = compliance_flags_for_treatment(t)
        if flags.davis_bacon_warning:
            davis_missing += 1
        treatment_rows.append(
            {
                "treatment_id": t.id,
                "road_name": road.road_name if road else None,
                "road_number": road.road_number if road else None,
                "district": int(road.district) if road and road.district is not None else None,
                "treatment_date": str(t.treatment_date),
                "miles_treated": float(t.miles_treated),
                "acres_treated": round(acres, 6),
                "treatment_type": t.treatment_type,
                "contractor": t.contractor,
            }
        )

    date_filter = (cast(Waypoint.created_at, Date) >= period_start) & (
        cast(Waypoint.created_at, Date) <= period_end
    )
    base_wp = select(func.count()).select_from(Waypoint).where(Waypoint.deleted_at.is_(None)).where(date_filter)

    signs = int(
        db.execute(
            base_wp.where(func.lower(func.coalesce(Waypoint.waypoint_type, "")) == "sign")
        ).scalar_one()
        or 0
    )
    mile_markers = int(
        db.execute(
            base_wp.where(func.lower(func.coalesce(Waypoint.waypoint_type, "")) == "mile_marker")
        ).scalar_one()
        or 0
    )

    buy_missing = int(
        db.execute(
            select(func.count())
            .select_from(Waypoint)
            .where(Waypoint.deleted_at.is_(None))
            .where(date_filter)
            .where(Waypoint.buy_america_certified.is_(False))
            .where(func.coalesce(Waypoint.material_cost, 0) > 0)
        ).scalar_one()
        or 0
    )

    return {
        "period_start": str(period_start),
        "period_end": str(period_end),
        "total_miles_treated": round(total_miles, 6),
        "total_acres_treated": round(total_acres, 6),
        "roads_completed_count": roads_completed,
        "roads_partial_count": roads_partial,
        "match_ratio": match_ratio,
        "treatments": treatment_rows,
        "waypoints_summary": {"signs_placed": signs, "mile_markers_placed": mile_markers},
        "compliance_flags": {
            "davis_bacon_missing_count": davis_missing,
            "buy_america_missing_count": buy_missing,
        },
    }


def _gps_pair(
    t_sx: float | None,
    t_sy: float | None,
    t_ex: float | None,
    t_ey: float | None,
    tr_sx: float | None,
    tr_sy: float | None,
    tr_ex: float | None,
    tr_ey: float | None,
) -> tuple[dict[str, float] | None, dict[str, float] | None]:
    slon = float(t_sx) if t_sx is not None else (float(tr_sx) if tr_sx is not None else None)
    slat = float(t_sy) if t_sy is not None else (float(tr_sy) if tr_sy is not None else None)
    elon = float(t_ex) if t_ex is not None else (float(tr_ex) if tr_ex is not None else None)
    elat = float(t_ey) if t_ey is not None else (float(tr_ey) if tr_ey is not None else None)
    start = {"lon": slon, "lat": slat} if slon is not None and slat is not None else None
    end = {"lon": elon, "lat": elat} if elon is not None and elat is not None else None
    return start, end


def generate_invoice_support(db: Session, period_start: date, period_end: date) -> dict[str, Any]:
    """
    Structured reimbursement support for USDA: line items with road, treatment, acres, GPS, contractor,
    task order, match flag, federal amount; plus period totals.
    """
    stmt = (
        select(
            Treatment,
            Road.road_name,
            Road.road_number,
            Road.district,
            func.ST_X(Treatment.gps_start),
            func.ST_Y(Treatment.gps_start),
            func.ST_X(Treatment.gps_end),
            func.ST_Y(Treatment.gps_end),
            func.ST_X(Track.start_gps),
            func.ST_Y(Track.start_gps),
            func.ST_X(Track.end_gps),
            func.ST_Y(Track.end_gps),
        )
        .join(Road, Treatment.road_id == Road.id)
        .outerjoin(Track, Treatment.track_id == Track.id)
        .where(Treatment.treatment_date >= period_start)
        .where(Treatment.treatment_date <= period_end)
        .where(Treatment.deleted_at.is_(None))
        .order_by(Treatment.treatment_date, Treatment.id)
    )
    raw_rows = db.execute(stmt).all()

    line_items: list[dict[str, Any]] = []
    total_miles = 0.0
    total_acres = 0.0
    total_fed = 0.0
    total_match_doc = 0.0

    for row in raw_rows:
        t = row[0]
        road_name, road_number, district = row[1], row[2], row[3]
        tsx, tsy, tex, tey = row[4], row[5], row[6], row[7]
        trx, tr_sy, trex, tr_ey = row[8], row[9], row[10], row[11]
        start, end = _gps_pair(tsx, tsy, tex, tey, trx, tr_sy, trex, tr_ey)
        miles = float(t.miles_treated)
        acres = float(t.acres_treated) if t.acres_treated is not None else calculate_acres(miles)
        total_miles += miles
        total_acres += acres
        af = float(t.amount_federal or 0)
        total_fed += af
        if t.match_documented:
            total_match_doc += float(t.amount_match or 0)
        line_items.append(
            {
                "treatment_id": t.id,
                "road_name": road_name,
                "road_number": road_number,
                "district": int(district) if district is not None else None,
                "treatment_date": str(t.treatment_date),
                "treatment_type": t.treatment_type,
                "miles_treated": miles,
                "acres_treated": round(acres, 6),
                "gps_start": start,
                "gps_end": end,
                "contractor": t.contractor,
                "contractor_task_order": t.contractor_task_order,
                "match_documented": bool(t.match_documented),
                "amount_federal": af if t.amount_federal is not None else None,
            }
        )

    return {
        "period_start": str(period_start),
        "period_end": str(period_end),
        "line_items": line_items,
        "totals": {
            "treatment_count": len(line_items),
            "total_miles": round(total_miles, 6),
            "total_acres": round(total_acres, 6),
            "total_federal_claimed": round(total_fed, 2),
            "total_match_documented": round(total_match_doc, 2),
        },
    }


def grant_progress_summary(db: Session) -> dict[str, Any]:
    r = db.execute(
        select(
            func.coalesce(func.sum(Road.cemp_miles), 0),
            func.coalesce(func.sum(Road.cbmp_miles), 0),
        )
    ).one()
    cemp = float(r[0] or 0)
    cbmp = float(r[1] or 0)
    pct = (cbmp / cemp * 100.0) if cemp > 0 else None
    return {"total_cemp_miles": cemp, "total_cbmp_miles": cbmp, "pct_complete": pct}
