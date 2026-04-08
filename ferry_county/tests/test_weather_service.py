from __future__ import annotations

import time

import backend.services.weather_service as ws


def test_get_current_weather_cached_within_ttl(monkeypatch) -> None:
    calls: list[int] = []

    def fake_noaa(_timeout: float) -> dict:
        calls.append(1)
        return {
            "temp_f": 55.0,
            "humidity_pct": 40.0,
            "wind_mph": 5.0,
            "wind_direction": "",
            "conditions": "Fair",
            "fire_weather_watch": False,
            "red_flag_warning": False,
            "forecast_summary": "",
            "alerts": [],
            "fire_weather_index": 40.0,
            "source": "noaa",
            "updated_at": "t",
        }

    monkeypatch.setattr(ws, "_fetch_gaia_attempt", lambda _t: None)
    monkeypatch.setattr(ws, "_fetch_noaa_bundle", fake_noaa)
    monkeypatch.setattr(ws, "TTL_SEC", 3600)
    ws._CACHE = {}
    ws._CACHE_TS = 0.0

    t = {"v": 0.0}

    def mono() -> float:
        return t["v"]

    monkeypatch.setattr(time, "monotonic", mono)
    t["v"] = 100.0
    a = ws.get_current_weather(force_refresh=True)
    t["v"] = 200.0
    b = ws.get_current_weather()
    assert len(calls) == 1
    assert a["temp_f"] == b["temp_f"] == 55.0
