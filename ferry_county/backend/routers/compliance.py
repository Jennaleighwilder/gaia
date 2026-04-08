from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.api import QuarterlyReportCreate
from backend.services.compliance_engine import (
    create_quarterly_financial_report,
    generate_invoice_support,
    generate_semi_annual_report,
    grant_progress_summary,
    match_ratio_summary,
    reimbursement_package,
)
from backend.services.compliance_spatial_export import treatments_period_geojson, treatments_period_kmz_bytes
from backend.services.invoice_support_pdf import build_invoice_support_csv, build_invoice_support_pdf

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/match-ratio")
def get_match_ratio(db: Session = Depends(get_db)) -> dict:
    """Aggregate federal vs documented match; compliant if match share >= program minimum (default 25%)."""
    return match_ratio_summary(db)


@router.get("/export/geojson")
def export_treatments_geojson(
    db: Session = Depends(get_db),
    period_start: date = Query(..., description="Inclusive start (treatment_date)"),
    period_end: date = Query(..., description="Inclusive end (treatment_date)"),
) -> JSONResponse:
    if period_end < period_start:
        raise HTTPException(400, "period_end must be >= period_start")
    return JSONResponse(treatments_period_geojson(db, period_start=period_start, period_end=period_end))


@router.get("/export/kmz")
def export_treatments_kmz(
    db: Session = Depends(get_db),
    period_start: date = Query(...),
    period_end: date = Query(...),
) -> Response:
    if period_end < period_start:
        raise HTTPException(400, "period_end must be >= period_start")
    data = treatments_period_kmz_bytes(db, period_start=period_start, period_end=period_end)
    return Response(
        content=data,
        media_type="application/vnd.google-earth.kmz",
        headers={
            "Content-Disposition": 'attachment; filename="ferry_treatments_export.kmz"',
        },
    )


@router.post("/quarterly-report")
def post_quarterly_report(
    body: QuarterlyReportCreate,
    db: Session = Depends(get_db),
    _x_actor: str | None = Header(default=None, alias="X-Actor"),
) -> dict:
    row = create_quarterly_financial_report(
        db,
        quarter=body.quarter,
        federal_spend=body.federal_spend,
        match_cash=body.match_cash,
        match_inkind=body.match_inkind,
        submitted=body.submitted,
        submitted_date=body.submitted_date,
        notes=body.notes,
    )
    db.commit()
    return {
        "id": row.id,
        "quarter": row.quarter,
        "federal_spend": float(row.federal_spend) if row.federal_spend is not None else None,
        "match_cash": float(row.match_cash) if row.match_cash is not None else None,
        "match_inkind": float(row.match_inkind) if row.match_inkind is not None else None,
        "total_spend": float(row.total_spend) if row.total_spend is not None else None,
        "match_ratio": float(row.match_ratio) if row.match_ratio is not None else None,
        "submitted": row.submitted,
        "submitted_date": str(row.submitted_date) if row.submitted_date else None,
    }


@router.get("/reimbursement-package")
def reimbursement_package_endpoint(
    db: Session = Depends(get_db),
    period_start: date = Query(...),
    period_end: date = Query(...),
) -> dict:
    rows = reimbursement_package(db, period_start=period_start, period_end=period_end)
    return {"period_start": str(period_start), "period_end": str(period_end), "rows": rows, "count": len(rows)}


@router.get("/grant-progress")
def grant_progress(db: Session = Depends(get_db)) -> dict:
    return grant_progress_summary(db)


@router.get("/semi-annual-report")
def semi_annual_report(
    db: Session = Depends(get_db),
    period_start: date = Query(..., description="Inclusive start (treatment_date)"),
    period_end: date = Query(..., description="Inclusive end (treatment_date)"),
) -> dict:
    if period_end < period_start:
        raise HTTPException(400, "period_end must be >= period_start")
    return generate_semi_annual_report(db, period_start=period_start, period_end=period_end)


@router.get("/invoice-support", response_model=None)
def invoice_support(
    db: Session = Depends(get_db),
    start: date = Query(..., description="Inclusive period start (treatment_date)"),
    end: date = Query(..., description="Inclusive period end (treatment_date)"),
    export_format: str = Query(
        "json",
        alias="format",
        description="json (default), pdf, or csv",
    ),
):
    if end < start:
        raise HTTPException(400, "end must be >= start")
    ef = export_format.lower().strip()
    if ef not in ("json", "pdf", "csv"):
        raise HTTPException(400, "format must be json, pdf, or csv")
    data = generate_invoice_support(db, period_start=start, period_end=end)
    if ef == "json":
        return JSONResponse(data)
    if ef == "pdf":
        body = build_invoice_support_pdf(data)
        return Response(
            content=body,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="ferry_cwdg_invoice_support.pdf"'},
        )
    body = build_invoice_support_csv(data)
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ferry_cwdg_invoice_support.csv"'},
    )
