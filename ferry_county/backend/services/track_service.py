from __future__ import annotations

import math
from datetime import datetime

from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session

from backend.models.road import Road
from backend.models.track import Track


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in statute miles (WGS84 sphere)."""
    r = 3958.7613
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(min(1.0, math.sqrt(a)))
    return r * c


def polyline_length_miles(points: list[tuple[float, float]]) -> float:
    """Sum segment lengths; points are (lat, lon)."""
    if len(points) < 2:
        return 0.0
    total = 0.0
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        total += haversine_miles(a[0], a[1], b[0], b[1])
    return total


def create_track(
    db: Session,
    *,
    road_id: int | None,
    points: list[dict],
    start_time: datetime | None,
    end_time: datetime | None,
    actor: str | None,
) -> Track:
    """
    points: [{"lon": float, "lat": float, "accuracy_m": optional}, ...] min 2 vertices.
    """
    if len(points) < 2:
        raise ValueError("at least two GPS points required for a track")
    if road_id is not None:
        if db.get(Road, road_id) is None:
            raise ValueError("road not found")

    coords_latlon: list[tuple[float, float]] = []
    for p in points:
        lon = float(p["lon"])
        lat = float(p["lat"])
        coords_latlon.append((lat, lon))

    # WKT uses lon lat order
    wkt_coords = ", ".join(f"{p['lon']} {p['lat']}" for p in points)
    line_wkt = f"LINESTRING({wkt_coords})"
    start_wkt = f"POINT({points[0]['lon']} {points[0]['lat']})"
    end_wkt = f"POINT({points[-1]['lon']} {points[-1]['lat']})"

    miles = polyline_length_miles(coords_latlon)
    raw = {
        "points": points,
        "vertex_count": len(points),
    }

    row = Track(
        road_id=road_id,
        start_time=start_time,
        end_time=end_time,
        start_gps=WKTElement(start_wkt, srid=4326),
        end_gps=WKTElement(end_wkt, srid=4326),
        track_line=WKTElement(line_wkt, srid=4326),
        calculated_miles=miles,
        raw_gps_log=raw,
        created_by=actor,
    )
    db.add(row)
    db.flush()
    return row
