from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_roads_search_empty_query_returns_400() -> None:
    client = TestClient(app)
    assert client.get("/roads/search").status_code == 400
    assert client.get("/roads/search?q=").status_code == 400
    assert client.get("/roads/search?q=%20%20").status_code == 400


def test_roads_search_query_too_long_returns_422() -> None:
    client = TestClient(app)
    long_q = "x" * 201
    r = client.get("/roads/search", params={"q": long_q})
    assert r.status_code == 422
