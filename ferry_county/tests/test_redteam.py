from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from backend.config import reset_settings_cache
from backend.main import app
from backend.services.kml_path_security import (
    KmzPathImportNotAllowed,
    KmzPathNotAllowed,
    resolve_and_validate_kmz_path,
)
from backend.services.kml_parse import parse_kmz_bytes


def test_parse_kmz_bytes_matches_file_parse(minimal_kmz_path: str) -> None:
    with open(minimal_kmz_path, "rb") as f:
        data = f.read()
    a = parse_kmz_bytes(data)
    assert len(a) == 1


def test_zip_without_doc_kml_raises() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("other.txt", b"nope")
    buf.seek(0)
    with pytest.raises(ValueError, match="doc.kml"):
        parse_kmz_bytes(buf.read())


def test_path_import_disabled_by_default() -> None:
    reset_settings_cache()
    with pytest.raises(KmzPathImportNotAllowed):
        resolve_and_validate_kmz_path("/etc/passwd")


def test_path_prefix_enforcement(tmp_path, monkeypatch) -> None:
    from backend.config import Settings, get_settings

    p = tmp_path / "a.kmz"
    p.write_bytes(b"PK\x03\x04")  # invalid but exists - actually need valid zip for realpath check
    # Create minimal valid kmz
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "doc.kml",
            b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document></Document></kml>""",
        )
    p.write_bytes(buf.getvalue())

    monkeypatch.setenv("ALLOW_KMZ_PATH_IMPORT", "true")
    monkeypatch.setenv("KMZ_PATH_ALLOW_PREFIXES", str(tmp_path))
    get_settings.cache_clear()

    resolved = resolve_and_validate_kmz_path(str(p))
    assert resolved.endswith("a.kmz")

    monkeypatch.setenv("KMZ_PATH_ALLOW_PREFIXES", "/nope")
    get_settings.cache_clear()
    with pytest.raises(KmzPathNotAllowed):
        resolve_and_validate_kmz_path(str(p))


def test_import_kmz_api_path_forbidden_by_default(minimal_kmz_path: str) -> None:
    reset_settings_cache()
    client = TestClient(app)
    r = client.post("/gis/import-kmz", json={"kmz_path": minimal_kmz_path})
    assert r.status_code == 403
