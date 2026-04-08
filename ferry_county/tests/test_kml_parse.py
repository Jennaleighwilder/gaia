from __future__ import annotations

from backend.services.kml_parse import parse_kmz_roads


def test_parse_minimal_kmz(minimal_kmz_path: str) -> None:
    roads = parse_kmz_roads(minimal_kmz_path)
    assert len(roads) == 1
    r = roads[0]
    assert r.is_lapr is True
    assert r.road_name == "Fixture Rd"
    assert r.source_feature_id.startswith("fc_")
    assert "MULTILINESTRING" in r.geometry_wkt
