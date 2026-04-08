from __future__ import annotations

import hashlib


def compute_source_feature_id(*, folder_path: str, name: str, geometry_wkt: str) -> str:
    """
    Deterministic ID for a road segment. Never use road name alone — v2 KMZ may omit Placemark id.
    Same inputs always yield the same id (re-import safe).
    """
    payload = f"{folder_path}|{name}|{geometry_wkt}".encode("utf-8")
    return "fc_" + hashlib.sha256(payload).hexdigest()[:16]
