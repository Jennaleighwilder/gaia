from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_db
from backend.schemas.api import ImportKmzBody
from backend.services.gis_export import roads_geojson, roads_kmz_bytes
from backend.services.kml_path_security import (
    KmzPathImportNotAllowed,
    KmzPathNotAllowed,
    resolve_and_validate_kmz_path,
)
from backend.services.seed_kmz import import_kmz_file, import_kmz_upload

router = APIRouter(prefix="/gis", tags=["gis"])

# Hard cap on uploaded KMZ archive size (bytes).
MAX_KMZ_UPLOAD_BYTES = 30 * 1024 * 1024


@router.post("/import-kmz-upload")
async def import_kmz_upload_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    data = await file.read()
    if len(data) > MAX_KMZ_UPLOAD_BYTES:
        raise HTTPException(413, f"KMZ too large (max {MAX_KMZ_UPLOAD_BYTES} bytes)")
    if not file.filename or not file.filename.lower().endswith(".kmz"):
        raise HTTPException(400, "expected a .kmz file")
    try:
        return import_kmz_upload(db, data, actor="api-upload")
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/import-kmz")
def import_kmz_path(body: ImportKmzBody, db: Session = Depends(get_db)) -> dict:
    """Trusted-automation only: requires allow_kmz_path_import + optional path prefixes."""
    try:
        safe = resolve_and_validate_kmz_path(body.kmz_path)
    except KmzPathImportNotAllowed as e:
        raise HTTPException(403, str(e)) from e
    except KmzPathNotAllowed as e:
        raise HTTPException(403, str(e)) from e
    except FileNotFoundError:
        raise HTTPException(400, f"kmz not found: {body.kmz_path}") from None
    try:
        return import_kmz_file(db, safe, actor="api-path")
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@router.get("/export/geojson")
def export_geojson(db: Session = Depends(get_db), treated_only: bool = False) -> JSONResponse:
    return JSONResponse(roads_geojson(db, treated_only=treated_only))


@router.get("/export/kmz")
def export_kmz(db: Session = Depends(get_db), treated_only: bool = False) -> Response:
    data = roads_kmz_bytes(db, treated_only=treated_only)
    return Response(content=data, media_type="application/vnd.google-earth.kmz")


@router.get("/security-config")
def security_config() -> dict:
    """Expose non-secret safety flags for operators (no DB)."""
    s = get_settings()
    return {
        "allow_kmz_path_import": s.allow_kmz_path_import,
        "has_path_prefix_restrictions": bool(s.kmz_path_allow_prefixes.strip()),
    }
