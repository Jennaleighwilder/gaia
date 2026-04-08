"""Public safety portal — no authentication."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.public_portal_service import (
    evacuation_zones_geojson,
    incidents_geojson,
    public_status_bundle,
    road_closures_public,
)
from backend.services.weather_service import get_current_weather

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/status")
def public_status(db: Session = Depends(get_db)) -> dict:
    return public_status_bundle(db)


@router.get("/evacuation-zones")
def public_evac_zones(db: Session = Depends(get_db)) -> JSONResponse:
    return JSONResponse(evacuation_zones_geojson(db))


@router.get("/road-closures")
def public_road_closures(db: Session = Depends(get_db)) -> dict:
    return {"items": road_closures_public(db)}


@router.get("/incidents")
def public_incidents(db: Session = Depends(get_db)) -> JSONResponse:
    return JSONResponse(incidents_geojson(db))


@router.get("/weather")
def public_weather() -> dict:
    return get_current_weather()
