from __future__ import annotations

import json
import zipfile
from io import BytesIO
from datetime import date
from xml.sax.saxutils import escape

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.road import Road
from backend.models.treatment import Treatment


def treatments_period_geojson(
    db: Session,
    *,
    period_start: date,
    period_end: date,
) -> dict:
    """
    One GeoJSON feature per treatment in the date range; geometry is the road centerline
    (MultiLineString) for annual spatial submission packages.
    """
    q = (
        select(
            Treatment.id,
            Treatment.road_id,
            Treatment.treatment_date,
            Treatment.miles_treated,
            Treatment.acres_treated,
            Treatment.contractor,
            Treatment.treatment_type,
            Road.source_feature_id,
            Road.road_name,
            func.ST_AsGeoJSON(Road.geometry, 6).label("geom"),
        )
        .join(Road, Road.id == Treatment.road_id)
        .where(Treatment.deleted_at.is_(None))
        .where(Road.deleted_at.is_(None))
        .where(Treatment.treatment_date >= period_start)
        .where(Treatment.treatment_date <= period_end)
        .order_by(Treatment.treatment_date, Treatment.id)
    )
    rows = db.execute(q).all()
    feats = []
    for (
        tid,
        road_id,
        tdate,
        miles,
        acres,
        contractor,
        ttype,
        sfid,
        rname,
        gj,
    ) in rows:
        feats.append(
            {
                "type": "Feature",
                "id": tid,
                "properties": {
                    "treatment_id": tid,
                    "road_id": road_id,
                    "source_feature_id": sfid,
                    "road_name": rname,
                    "treatment_date": str(tdate),
                    "miles_treated": float(miles) if miles is not None else None,
                    "acres_treated": float(acres) if acres is not None else None,
                    "contractor": contractor,
                    "treatment_type": ttype,
                },
                "geometry": json.loads(gj) if gj else None,
            }
        )
    return {"type": "FeatureCollection", "features": feats}


def treatments_period_kmz_bytes(
    db: Session,
    *,
    period_start: date,
    period_end: date,
) -> bytes:
    gj = treatments_period_geojson(db, period_start=period_start, period_end=period_end)
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        "<Document><name>Ferry County Treatments Spatial Export</name>",
    ]
    for f in gj.get("features", []):
        geom = f.get("geometry")
        props = f.get("properties") or {}
        if not geom:
            continue
        name = escape(str(props.get("road_name") or "treatment"))
        desc_parts = [
            f"treatment_id: {props.get('treatment_id')}",
            f"treatment_date: {props.get('treatment_date')}",
            f"miles_treated: {props.get('miles_treated')}",
            f"acres_treated: {props.get('acres_treated')}",
            f"contractor: {props.get('contractor')}",
            f"treatment_type: {props.get('treatment_type')}",
            f"source_feature_id: {props.get('source_feature_id')}",
        ]
        desc_blob = "<br/>".join(str(x) for x in desc_parts)
        parts.append("<Placemark>")
        parts.append(f"<name>{name}</name>")
        parts.append(f"<description><![CDATA[{desc_blob}]]></description>")
        gtype = geom.get("type")
        coords = geom.get("coordinates")
        parts.append("<MultiGeometry>")
        if gtype == "MultiLineString" and coords:
            for line in coords:
                coord_blob = " ".join(f"{lon},{lat},0" for lon, lat in line)
                parts.append("<LineString><tessellate>1</tessellate>")
                parts.append(f"<coordinates>{coord_blob}</coordinates>")
                parts.append("</LineString>")
        elif gtype == "LineString" and coords:
            coord_blob = " ".join(f"{lon},{lat},0" for lon, lat in coords)
            parts.append("<LineString><tessellate>1</tessellate>")
            parts.append(f"<coordinates>{coord_blob}</coordinates>")
            parts.append("</LineString>")
        parts.append("</MultiGeometry>")
        parts.append("</Placemark>")
    parts.append("</Document></kml>")
    kml = "\n".join(parts).encode("utf-8")
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", kml)
    return buf.getvalue()
