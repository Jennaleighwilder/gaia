from __future__ import annotations

import json
import zipfile
from io import BytesIO
from xml.sax.saxutils import escape

from sqlalchemy import func, select, text
from sqlalchemy.sql.selectable import Select
from sqlalchemy.orm import Session

from backend.models.road import Road


def roads_field_map_geojson(db: Session) -> dict:
    """Roads for Field map: geometry + treatment_status + grant flag (CEMP miles > 0)."""
    q: Select = select(
        Road.id,
        Road.source_feature_id,
        Road.road_name,
        Road.treatment_status,
        Road.cemp_miles,
        func.ST_AsGeoJSON(Road.geometry, 6).label("geom"),
    ).where(Road.deleted_at.is_(None))
    rows = db.execute(q).all()
    feats = []
    for rid, sfid, name, status, cemp, gj in rows:
        cemp_f = float(cemp) if cemp is not None else 0.0
        feats.append(
            {
                "type": "Feature",
                "id": rid,
                "properties": {
                    "road_id": rid,
                    "source_feature_id": sfid,
                    "road_name": name,
                    "treatment_status": status,
                    "is_grant_road": cemp_f > 0,
                },
                "geometry": json.loads(gj) if gj else None,
            }
        )
    return {"type": "FeatureCollection", "features": feats}


def roads_geojson(db: Session, *, treated_only: bool = False) -> dict:
    q: Select = select(
        Road.id,
        Road.source_feature_id,
        Road.road_name,
        Road.treatment_status,
        func.ST_AsGeoJSON(Road.geometry, 6).label("geom"),
    ).where(Road.deleted_at.is_(None))
    if treated_only:
        q = q.where(Road.treatment_status != "untreated")
    rows = db.execute(q).all()
    feats = []
    for rid, sfid, name, status, gj in rows:
        feats.append(
            {
                "type": "Feature",
                "id": rid,
                "properties": {
                    "source_feature_id": sfid,
                    "road_name": name,
                    "treatment_status": status,
                },
                "geometry": json.loads(gj) if gj else None,
            }
        )
    return {"type": "FeatureCollection", "features": feats}


def roads_kmz_bytes(db: Session, *, treated_only: bool = False) -> bytes:
    gj = roads_geojson(db, treated_only=treated_only)
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        "<Document><name>Ferry County Roads Export</name>",
    ]
    for f in gj.get("features", []):
        geom = f.get("geometry")
        if not geom or geom["type"] != "MultiLineString":
            continue
        lines = geom["coordinates"]
        props = f.get("properties") or {}
        name = escape(str(props.get("road_name") or "road"))
        sfid = escape(str(props.get("source_feature_id") or ""))
        parts.append("<Placemark>")
        parts.append(f"<name>{name}</name>")
        parts.append(f"<description><![CDATA[source_feature_id: {sfid}]]></description>")
        parts.append("<MultiGeometry>")
        for line in lines:
            coord_blob = " ".join(f"{lon},{lat},0" for lon, lat in line)
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


def refresh_road_geometry_stats(db: Session, road_id: int) -> None:
    """Optional: set length_mi from geometry if null — uses geography for approximate meters."""
    db.execute(
        text(
            """
            UPDATE roads
            SET length_mi = COALESCE(length_mi, ST_Length(geometry::geography) / 1609.344)
            WHERE id = :rid
            """
        ),
        {"rid": road_id},
    )
