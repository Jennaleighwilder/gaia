"""
Live weather for Ferry County — GAIA bundle first, NOAA api.weather.gov fallback.
15-minute process-local cache. Shared shape for /public/weather and SENTINEL atmosphere hints.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)

NOAA_HEADERS = {"User-Agent": "FerryCWDG-Weather/1.0 (Ferry County; public safety)"}
FERRY_LAT = 48.65
FERRY_LON = -118.6

_CACHE: dict[str, Any] = {}
_CACHE_TS = 0.0
TTL_SEC = 15 * 60


def _parse_mph(s: str | None) -> float:
    if not s:
        return 0.0
    m = re.search(r"([\d.]+)\s*mph", str(s), re.I)
    if m:
        return float(m.group(1))
    m2 = re.search(r"([\d.]+)", str(s))
    return float(m2.group(1)) if m2 else 0.0


def _noaa_alerts_flags(client: httpx.Client) -> tuple[list[str], bool, bool]:
    alerts: list[str] = []
    red_flag = False
    fire_weather_watch = False
    r = client.get(
        "https://api.weather.gov/alerts/active",
        params={"point": f"{FERRY_LAT},{FERRY_LON}"},
    )
    if r.status_code != 200:
        return alerts, red_flag, fire_weather_watch
    for feat in (r.json().get("features") or []):
        props = feat.get("properties") or {}
        event = str(props.get("event") or "")
        head = str(props.get("headline") or "")
        text = f"{event} — {head}".strip(" —")
        if text:
            alerts.append(text)
        el = event.lower()
        if "red flag" in el or "red flag" in head.lower():
            red_flag = True
        if "fire weather" in el:
            fire_weather_watch = True
    return alerts, red_flag, fire_weather_watch


def _fetch_noaa_bundle(timeout: float) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    with httpx.Client(timeout=timeout, headers=NOAA_HEADERS, follow_redirects=True) as client:
        pt = client.get(f"https://api.weather.gov/points/{FERRY_LAT},{FERRY_LON}")
        pt.raise_for_status()
        props = pt.json().get("properties") or {}
        hourly_url = props.get("forecastHourly")
        if not hourly_url:
            raise ValueError("no forecastHourly")
        fc = client.get(hourly_url)
        fc.raise_for_status()
        periods = (fc.json().get("properties") or {}).get("periods") or []
        p0 = periods[0] if periods else {}
        temp = float(p0.get("temperature") or 60)
        unit = str(p0.get("temperatureUnit") or "F")
        if unit.upper().startswith("C"):
            temp_f = temp * 9.0 / 5.0 + 32.0
        else:
            temp_f = temp
        rh = float(p0.get("relativeHumidity") or 40)
        wind_mph = _parse_mph(p0.get("windSpeed"))
        wd = str(p0.get("windDirection") or "")
        cond = str(p0.get("shortForecast") or "")
        summary = str(p0.get("detailedForecast") or cond)[:800]
        alerts, red_flag, fww = _noaa_alerts_flags(client)
        fwi = (temp_f - 32.0) * 0.4 + (100.0 - rh) * 0.3 + wind_mph * 0.3
        fwi = max(0.0, min(100.0, fwi))
        return {
            "temp_f": round(temp_f, 1),
            "humidity_pct": round(rh, 1),
            "wind_mph": round(wind_mph, 1),
            "wind_direction": wd,
            "conditions": cond,
            "fire_weather_watch": fww,
            "red_flag_warning": red_flag,
            "forecast_summary": summary,
            "alerts": alerts,
            "fire_weather_index": round(fwi, 1),
            "source": "noaa",
            "updated_at": now,
        }


def _fetch_gaia_attempt(timeout: float) -> dict[str, Any] | None:
    url = (get_settings().gaia_weather_bundle_url or "").strip()
    if not url:
        return None
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            r = client.get(url)
            if r.status_code != 200:
                return None
            data = r.json()
    except Exception as e:
        logger.debug("GAIA weather bundle unavailable: %s", e)
        return None
    now = datetime.now(timezone.utc).isoformat()
    # Accept flexible keys from GAIA bundle
    temp = float(data.get("temp_f") or data.get("temperature_f") or 55)
    rh = float(data.get("humidity_pct") or data.get("relative_humidity") or 40)
    wind = float(data.get("wind_mph") or data.get("wind_speed_mph") or 5)
    wdir = str(data.get("wind_direction") or "")
    cond = str(data.get("conditions") or data.get("short_forecast") or "")
    alerts = data.get("alerts") if isinstance(data.get("alerts"), list) else []
    rf = bool(data.get("red_flag_warning") or data.get("red_flag"))
    fww = bool(data.get("fire_weather_watch"))
    fwi = float(data.get("fire_weather_index") or (temp - 32) * 0.4 + (100 - rh) * 0.3 + wind * 0.3)
    fwi = max(0.0, min(100.0, fwi))
    return {
        "temp_f": round(temp, 1),
        "humidity_pct": round(rh, 1),
        "wind_mph": round(wind, 1),
        "wind_direction": wdir,
        "conditions": cond,
        "fire_weather_watch": fww,
        "red_flag_warning": rf,
        "forecast_summary": str(data.get("forecast_summary") or cond)[:800],
        "alerts": [str(a) for a in alerts],
        "fire_weather_index": round(fwi, 1),
        "source": "gaia",
        "updated_at": now,
    }


def get_current_weather(*, force_refresh: bool = False) -> dict[str, Any]:
    global _CACHE_TS, _CACHE
    now = time.monotonic()
    if not force_refresh and _CACHE and (now - _CACHE_TS) < TTL_SEC:
        return dict(_CACHE)

    timeout = float(get_settings().sentinel_http_timeout_s)
    payload = _fetch_gaia_attempt(timeout)
    if payload is None:
        try:
            payload = _fetch_noaa_bundle(timeout)
        except Exception as e:
            logger.warning("NOAA weather fallback failed: %s", e)
            payload = {
                "temp_f": 55.0,
                "humidity_pct": 50.0,
                "wind_mph": 5.0,
                "wind_direction": "",
                "conditions": "Unavailable",
                "fire_weather_watch": False,
                "red_flag_warning": False,
                "forecast_summary": "Weather data temporarily unavailable.",
                "alerts": [],
                "fire_weather_index": 40.0,
                "source": "unavailable",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

    _CACHE = payload
    _CACHE_TS = now
    return dict(payload)
