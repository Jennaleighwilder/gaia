from __future__ import annotations

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.models.road import Road
from backend.services.kml_parse import ParsedRoad, parse_kmz_bytes, parse_kmz_roads


def _import_parsed_roads(db: Session, parsed: list[ParsedRoad], *, actor: str | None = "system") -> dict[str, int]:
    lapr = sum(1 for p in parsed if p.is_lapr)
    inserted = 0
    for p in parsed:
        exists = db.execute(select(Road.id).where(Road.source_feature_id == p.source_feature_id)).scalar_one_or_none()
        if exists:
            continue
        inserted += 1
        db.execute(
            text(
                """
                INSERT INTO roads (
                    source_feature_id, road_number, road_name, district, jurisdiction, federal_class,
                    length_mi, cemp_miles, cbmp_miles, begin_point, end_point, treatment_status,
                    geometry, kml_folder_path, created_by, created_at, updated_at
                ) VALUES (
                    :source_feature_id, :road_number, :road_name, NULL, NULL, :federal_class,
                    :length_mi, :cemp_miles, 0, NULL, NULL, 'untreated',
                    ST_SetSRID(ST_GeomFromText(:wkt), 4326), :kml_folder_path, :created_by,
                    NOW(), NOW()
                )
                """
            ),
            {
                "source_feature_id": p.source_feature_id,
                "road_number": p.road_number,
                "road_name": p.road_name,
                "federal_class": p.federal_class,
                "length_mi": p.length_mi,
                "cemp_miles": p.cemp_miles,
                "wkt": p.geometry_wkt,
                "kml_folder_path": p.kml_folder_path,
                "created_by": actor,
            },
        )
    db.commit()
    total = db.execute(select(func.count()).select_from(Road)).scalar_one()
    return {"inserted": inserted, "parsed_in_file": len(parsed), "lapr_segments_in_file": lapr, "roads_rows_total": int(total)}


def import_kmz_file(db: Session, kmz_path: str, *, actor: str | None = "system") -> dict[str, int]:
    parsed = parse_kmz_roads(kmz_path)
    return _import_parsed_roads(db, parsed, actor=actor)


def import_kmz_upload(db: Session, data: bytes, *, actor: str | None = "system") -> dict[str, int]:
    parsed = parse_kmz_bytes(data)
    return _import_parsed_roads(db, parsed, actor=actor)
