from __future__ import annotations

from backend.services.stable_id import compute_source_feature_id


def test_stable_id_deterministic():
    a = compute_source_feature_id(folder_path="/a", name="X", geometry_wkt="MULTILINESTRING ((0 0, 1 1))")
    b = compute_source_feature_id(folder_path="/a", name="X", geometry_wkt="MULTILINESTRING ((0 0, 1 1))")
    assert a == b
    c = compute_source_feature_id(folder_path="/a", name="Y", geometry_wkt="MULTILINESTRING ((0 0, 1 1))")
    assert c != a
