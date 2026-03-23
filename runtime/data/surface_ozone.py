"""
Surface Ozone from EPA AirNow — tropopause fold / jet stream forcing indicator.

Rising ozone without local pollution = stratospheric descent = dynamic forcing.
Data: https://www.airnow.gov/

For backtest: reads from fixture. For live: AirNow API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

# East TN AirNow monitors: Knoxville, Tri-Cities, etc.
FIXTURE_PATH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "surface_ozone.json"


def load_fixture() -> dict:
    """Load ozone fixture: { "YYYY-MM-DD": ppb or { "station": ppb } }."""
    if not FIXTURE_PATH.exists():
        return {}
    try:
        return json.loads(FIXTURE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def get_surface_ozone_ppb(date_str: str, station_id: Optional[str] = None) -> Optional[float]:
    """
    Get surface ozone in ppb for a date.
    Returns None if no data.
    """
    fixture = load_fixture()
    date_key = str(date_str)[:10]
    day_data = fixture.get(date_key)
    if day_data is None:
        return None
    if isinstance(day_data, (int, float)):
        return float(day_data)
    if isinstance(day_data, dict) and station_id:
        for key in (station_id, station_id.replace("K", ""), "TYS", "TRI", "default"):
            if key and key in day_data:
                return float(day_data[key])
        vals = [v for v in day_data.values() if isinstance(v, (int, float))]
        return float(vals[0]) if vals else None
    return None
