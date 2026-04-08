from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.api import TreatmentCreate
from backend.services.compliance_engine import reimbursement_record
from backend.services.treatment_service import create_treatment

router = APIRouter(prefix="/treatments", tags=["treatments"])


@router.post("/roads/{road_id}")
def post_treatment(
    road_id: int,
    body: TreatmentCreate,
    db: Session = Depends(get_db),
    x_actor: str | None = Header(default=None, alias="X-Actor"),
) -> dict:
    try:
        t = create_treatment(
            db,
            road_id=road_id,
            treatment_date=body.treatment_date,
            miles_treated=body.miles_treated,
            treatment_type=body.treatment_type,
            contractor=body.contractor,
            contractor_task_order=body.contractor_task_order,
            contractor_invoice_amount=body.contractor_invoice_amount,
            logged_by=body.logged_by,
            match_documented=body.match_documented,
            match_source=body.match_source,
            match_amount=body.match_amount,
            amount_federal=body.amount_federal,
            amount_match=body.amount_match,
            davis_bacon_certified=body.davis_bacon_certified,
            davis_bacon_wage_rate=body.davis_bacon_wage_rate,
            notes=body.notes,
            actor=x_actor or "david",
            track_id=body.track_id,
            client_track_operation_id=body.client_track_operation_id,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return reimbursement_record(db, t.id)


@router.get("/{treatment_id}/reimbursement")
def get_reimbursement(treatment_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return reimbursement_record(db, treatment_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
