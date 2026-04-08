from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_public_weather_requires_no_auth(monkeypatch) -> None:
    stub = {
        "temp_f": 62.0,
        "humidity_pct": 35.0,
        "wind_mph": 8.0,
        "wind_direction": "W",
        "conditions": "Clear",
        "fire_weather_watch": False,
        "red_flag_warning": False,
        "forecast_summary": "Test",
        "alerts": [],
        "fire_weather_index": 45.0,
        "source": "test",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }

    monkeypatch.setattr("backend.routers.public.get_current_weather", lambda: stub)
    client = TestClient(app)
    r = client.get("/public/weather")
    assert r.status_code == 200
    data = r.json()
    assert data["temp_f"] == 62.0
    assert data["source"] == "test"
