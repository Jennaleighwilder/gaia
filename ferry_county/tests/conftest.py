from __future__ import annotations

import os
import zipfile

import pytest


@pytest.fixture
def minimal_kmz_path(tmp_path) -> str:
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Folder><name>LAPR Grant Roads - Treatment Required</name>
<Placemark>
<name>Fixture Rd</name>
<description><![CDATA[<tr><td>Road #</td><td>00001</td></tr>
<tr><td>Grant Miles (CEMP)</td><td>1.0 mi</td></tr>
<tr><td>Road Length</td><td>1.0 mi</td></tr>]]></description>
<LineString><coordinates>-118.0,48.5,0 -118.01,48.51,0</coordinates></LineString>
</Placemark>
</Folder>
</Document></kml>"""
    p = tmp_path / "minimal.kmz"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("doc.kml", kml.encode("utf-8"))
    return str(p)


@pytest.fixture(scope="session")
def database_url() -> str | None:
    # Default matches docker-compose.yml (database `ferry`). Use a dedicated CI DB in production.
    return os.environ.get("DATABASE_URL", "postgresql+psycopg2://ferry:ferry@127.0.0.1:5434/ferry")


@pytest.fixture(scope="session")
def postgres_ready(database_url: str | None) -> bool:
    if not database_url:
        return False
    try:
        from sqlalchemy import create_engine, text

        eng = create_engine(database_url, pool_pre_ping=True)
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
