"""
GPS Precipitable Water Vapor — total column moisture from UCAR/NOAA GPS-Met.

Data: https://www.unavco.org/data/tropospheric/pwv/pwv.html
UCAR COSMIC processes GPS data hourly; PWV in mm.

For backtest: reads from fixture. For live: would fetch from UCAR API/files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

# East TN GPS-met co-located or nearby stations
# TYS Knoxville, TRI Tri-Cities; map ASOS station_id -> GPS site if different
STATION_ALIAS = {
    "KTYS": "TYS",
    "KTRI": "TRI",
    "KGKT": "GKT",
    "KCHA": "CHA",
    "KAVL": "AVL",
}

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "gps_pw.json"


def load_fixture() -> dict:
    """Load GPS-PW fixture: { "YYYY-MM-DD": { "TYS": mm, "TRI": mm, ... } }."""
    if not FIXTURE_PATH.exists():
        return {}
    try:
        return json.loads(FIXTURE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def get_gps_pw_mm(date_str: str, station_id: str) -> Optional[float]:
    """
    Get GPS precipitable water in mm for a station/date.
    Returns None if no data (fixture empty or missing).
    """
    fixture = load_fixture()
    date_key = str(date_str)[:10]
    station_key = STATION_ALIAS.get(station_id.upper() if station_id else "", station_id.upper().replace("K", "") if station_id else "")
    day_data = fixture.get(date_key, {})
    if not day_data:
        return None
    # Try station id, then without K, then any nearby
    for key in (station_id, station_key, station_id.replace("K", "") if station_id else ""):
        if key and key in day_data:
            return float(day_data[key])
    # Fallback: use first available for that date (regional proxy)
    vals = [v for v in day_data.values() if isinstance(v, (int, float))]
    return float(vals[0]) if vals else None


def get_precipitable_water_in(date_str: str, station_id: str) -> Optional[float]:
    """Get GPS-PW in inches (GAIA moisture engine expects inches)."""
    mm = get_gps_pw_mm(date_str, station_id)
    if mm is None:
        return None
    return round(mm / 25.4, 4)


def mm_to_climatology_score(mm: float) -> float:
    """
    East TN climatology: convert GPS-PW mm to 0–1 score.
    < 10mm = very dry = 0.0; 10–20 = 0.2; 20–30 = 0.4;
    30–40 = 0.6; 40–50 = 0.8; > 50mm = 1.0
    """
    if mm < 10:
        return 0.0
    if mm < 20:
        return 0.2
    if mm < 30:
        return 0.4
    if mm < 40:
        return 0.6
    if mm < 50:
        return 0.8
    return 1.0


def get_gps_pw_score(date_str: str, station_id: str) -> Optional[float]:
    """
    Get GPS-PW as 0–1 climatology score for backtest/channel_context.
    Returns None if fixture has no data for that date.
    """
    mm = get_gps_pw_mm(date_str, station_id)
    if mm is None:
        return None
    return mm_to_climatology_score(mm)
