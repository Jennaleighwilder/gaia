from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_db
from backend.models.attachment import Attachment
from backend.models.treatment import Treatment
from backend.models.waypoint import Waypoint
from backend.services.attachment_storage import blob_path_for_uri, save_uploaded_file, safe_original_filename
from backend.services.audit_service import write_audit

router = APIRouter(prefix="/attachments", tags=["attachments"])


class AttachmentRegister(BaseModel):
    file_name: str = Field(min_length=1, max_length=512)
    content_type: str | None = None
    sha256_hex: str = Field(min_length=64, max_length=64)
    kind: str = Field(
        description="invoice | photo | match_backup | davis_bacon_wage | buy_america_cert | export_manifest | other"
    )
    storage_uri: str = Field(min_length=1)
    treatment_id: int | None = None
    waypoint_id: int | None = None
    quarterly_financial_report_id: int | None = None


@router.post("")
def register_attachment(
    body: AttachmentRegister,
    db: Session = Depends(get_db),
    x_actor: str | None = Header(default=None, alias="X-Actor"),
) -> dict:
    if not body.treatment_id and not body.waypoint_id and not body.quarterly_financial_report_id:
        raise HTTPException(400, "link at least one of treatment_id, waypoint_id, quarterly_financial_report_id")
    row = Attachment(
        file_name=body.file_name,
        content_type=body.content_type,
        sha256_hex=body.sha256_hex.lower(),
        kind=body.kind,
        storage_uri=body.storage_uri,
        treatment_id=body.treatment_id,
        waypoint_id=body.waypoint_id,
        quarterly_financial_report_id=body.quarterly_financial_report_id,
        created_by=x_actor or "system",
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        table_name="attachments",
        record_id=row.id,
        action="create",
        actor=x_actor or "system",
        new_value={"kind": body.kind, "sha256": body.sha256_hex[:16]},
    )
    db.commit()
    return {"id": row.id, "sha256_hex": row.sha256_hex, "kind": body.kind}


@router.post("/upload")
async def upload_attachment(
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    kind: str = Form(
        description="invoice | photo | match_backup | davis_bacon_wage | buy_america_cert | export_manifest | other"
    ),
    treatment_id: int | None = Form(None),
    waypoint_id: int | None = Form(None),
    quarterly_financial_report_id: int | None = Form(None),
    x_actor: str | None = Header(default=None, alias="X-Actor"),
) -> dict:
    if not treatment_id and not waypoint_id and not quarterly_financial_report_id:
        raise HTTPException(400, "link at least one of treatment_id, waypoint_id, quarterly_financial_report_id")
    max_b = get_settings().max_attachment_bytes
    data = await file.read()
    if len(data) > max_b:
        raise HTTPException(400, f"file exceeds {max_b} bytes")
    if treatment_id is not None and db.get(Treatment, treatment_id) is None:
        raise HTTPException(400, "treatment not found")
    if waypoint_id is not None and db.get(Waypoint, waypoint_id) is None:
        raise HTTPException(400, "waypoint not found")
    sha, uri = save_uploaded_file(data, file.filename or "upload.bin")
    row = Attachment(
        file_name=safe_original_filename(file.filename or "upload.bin"),
        content_type=file.content_type,
        sha256_hex=sha,
        kind=kind,
        storage_uri=uri,
        treatment_id=treatment_id,
        waypoint_id=waypoint_id,
        quarterly_financial_report_id=quarterly_financial_report_id,
        created_by=x_actor or "field",
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        table_name="attachments",
        record_id=row.id,
        action="create",
        actor=x_actor or "field",
        new_value={"kind": kind, "sha256": sha[:16], "upload": True},
    )
    db.commit()
    return {
        "id": row.id,
        "sha256_hex": sha,
        "kind": kind,
        "storage_uri": uri,
        "file_name": row.file_name,
    }


@router.get("/{attachment_id}/file")
def download_attachment_file(attachment_id: int, db: Session = Depends(get_db)) -> FileResponse:
    row = db.get(Attachment, attachment_id)
    if row is None:
        raise HTTPException(404, "attachment not found")
    path = blob_path_for_uri(row.storage_uri)
    if path is None or not path.is_file():
        raise HTTPException(404, "stored file missing")
    return FileResponse(
        str(path),
        filename=row.file_name,
        media_type=row.content_type or "application/octet-stream",
    )


@router.get("")
def list_attachments(
    db: Session = Depends(get_db),
    treatment_id: int | None = None,
    waypoint_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    q = select(Attachment).order_by(Attachment.id.desc())
    if treatment_id is not None:
        q = q.where(Attachment.treatment_id == treatment_id)
    if waypoint_id is not None:
        q = q.where(Attachment.waypoint_id == waypoint_id)
    rows = db.execute(q.limit(limit)).scalars().all()
    return {
        "items": [
            {
                "id": a.id,
                "file_name": a.file_name,
                "kind": a.kind,
                "sha256_hex": a.sha256_hex,
                "treatment_id": a.treatment_id,
                "waypoint_id": a.waypoint_id,
                "content_type": a.content_type,
            }
            for a in rows
        ]
    }
