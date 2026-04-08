from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services import sentinel as sentinel_service

router = APIRouter(prefix="/sentinel", tags=["sentinel"])


@router.get("/status")
def sentinel_status(db: Session = Depends(get_db)) -> dict:
    summary = sentinel_service.get_latest_scan_summary(db)
    top = sentinel_service.get_top_risk_corridors(db, limit=3)
    return {
        "latest_scan": summary,
        "top_risk_roads": top,
        "healthy": summary is not None and bool(summary.get("scan_complete")),
    }


@router.get("/risks")
def list_risks(
    db: Session = Depends(get_db),
    level: str | None = Query(None, description="Filter: low | moderate | elevated | critical"),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    rows = sentinel_service.list_road_risks_for_latest_scan(db, level=level, limit=limit)
    return {"items": rows, "count": len(rows)}


@router.get("/risks/{road_id}")
def road_risk_detail(road_id: int, db: Session = Depends(get_db)) -> dict:
    detail = sentinel_service.get_road_risk_breakdown(db, road_id)
    if detail is None:
        raise HTTPException(404, "no scan data for this road")
    return detail


@router.post("/scan")
def trigger_scan(db: Session = Depends(get_db)) -> dict:
    out = sentinel_service.run_convergence_scan(db)
    return {
        "scan_id": out["scan_id"],
        "road_count": out["road_count"],
        "critical_count": out["critical_count"],
        "status": "complete",
    }


@router.get("/history/{road_id}")
def road_risk_history(
    road_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(30, ge=1, le=100),
) -> dict:
    items = sentinel_service.get_road_risk_history(db, road_id, max_scans=limit)
    return {"road_id": road_id, "items": items, "count": len(items)}
