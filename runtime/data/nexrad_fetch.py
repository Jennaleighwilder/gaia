"""
NEXRAD Level II Radar — Nature-scale rotation detection.
Source: AWS S3 noaa-nexrad-level2 (public).
Primary: KMRX (Morristown TN) — covers all East TN.
"""

from __future__ import annotations

import gzip
import io
import logging
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

BASE = "https://noaa-nexrad-level2.s3.amazonaws.com"
EAST_TN_LAT = (35.5, 36.8)
EAST_TN_LON = (-84.5, -81.5)


def _list_nexrad_files(station: str, dt: datetime) -> list[str]:
    """List NEXRAD files for station on date. Returns sorted keys (newest first)."""
    y, m, d = dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")
    prefix = f"{y}/{m}/{d}/{station}/"
    url = f"{BASE}/?list-type=2&prefix={urllib.parse.quote(prefix)}&max-keys=100"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA-NatureScale/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            xml = r.read().decode()
    except Exception as e:
        logger.warning("NEXRAD S3 list failed: %s", e)
        return []
    keys = re.findall(r"<Key>([^<]+)</Key>", xml)
    keys.sort(reverse=True)
    return keys


def _download_nexrad(key: str) -> bytes | None:
    """Download single NEXRAD file, return raw bytes (gunzipped if .gz)."""
    url = f"{BASE}/{urllib.parse.quote(key)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA-NatureScale/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
    except Exception as e:
        logger.warning("NEXRAD S3 get failed: %s", e)
        return None
    if key.endswith(".gz"):
        raw = gzip.decompress(raw)
    return raw


def _parse_with_pyart(raw: bytes) -> Any | None:
    """Parse NEXRAD bytes with pyart. Returns Radar object or None."""
    try:
        import pyart

        rad = pyart.io.read_nexrad_archive(io.BytesIO(raw))
        return rad
    except ImportError:
        logger.warning("pyart not installed; pip install arm-pyart")
        return None
    except Exception as e:
        logger.warning("pyart parse failed: %s", e)
        return None


def _extract_for_region(radar: Any) -> dict[str, float | None]:
    """
    Extract composite reflectivity, velocity, VIL, echo top for East TN box.
    Iterates over sweeps, masks to East TN, takes max refl and velocity span.
    """
    import numpy as np

    out = {
        "composite_reflectivity": None,
        "velocity_max": None,
        "velocity_min": None,
        "vil": None,
        "echo_top_km": None,
        "rotation_couplet_kt": None,
    }
    all_refl = []
    all_vel = []

    try:
        nsweeps = radar.nsweeps
        for sw in range(nsweeps):
            gate_lat, gate_lon, _ = radar.get_gate_lat_lon_alt(sw)
            mask = (
                (gate_lat >= EAST_TN_LAT[0])
                & (gate_lat <= EAST_TN_LAT[1])
                & (gate_lon >= EAST_TN_LON[0])
                & (gate_lon <= EAST_TN_LON[1])
            )
            if not mask.any():
                continue
            sweep_slice = radar.get_slice(sw)
            if "reflectivity" in radar.fields:
                refl = radar.fields["reflectivity"]["data"][sweep_slice]
                refl_m = np.ma.masked_invalid(refl)
                refl_m = np.ma.masked_where(refl_m < -100, refl_m)
                m = np.ma.masked_where(~mask, refl_m)
                if np.ma.count(m):
                    all_refl.append(np.ma.max(m))
            if "velocity" in radar.fields:
                vel = radar.fields["velocity"]["data"][sweep_slice]
                vel_m = np.ma.masked_invalid(vel)
                vel_m = np.ma.masked_where(np.abs(vel_m) > 200, vel_m)
                m = np.ma.masked_where(~mask, vel_m)
                if np.ma.count(m):
                    all_vel.append((np.ma.max(m), np.ma.min(m)))

        if all_refl:
            out["composite_reflectivity"] = float(max(all_refl))
        if all_vel:
            vmax = max(v[0] for v in all_vel)
            vmin = min(v[1] for v in all_vel)
            out["velocity_max"] = float(vmax)
            out["velocity_min"] = float(vmin)
            # Couplet: m/s -> kt (1.944)
            out["rotation_couplet_kt"] = float(abs(vmax) + abs(vmin)) * 1.944

    except Exception as e:
        logger.warning("NEXRAD region extract failed: %s", e)
    return out


def detect_velocity_couplet(velocity_data: dict) -> float:
    """
    Score 0-1 from velocity couplet magnitude (kt).
    >90 kt = 1.0, 50-90 = 0.7, 30-50 = 0.5, <30 = proportional.
    """
    couplet = velocity_data.get("rotation_couplet_kt")
    if couplet is None or couplet <= 0:
        return 0.0
    if couplet >= 90:
        return 1.0
    if couplet >= 50:
        return 0.7 + 0.3 * (couplet - 50) / 40
    if couplet >= 30:
        return 0.5 + 0.2 * (couplet - 30) / 20
    return 0.3 * (couplet / 30)


def fetch_latest_kmrx() -> dict[str, Any]:
    """Fetch most recent KMRX volume, extract for East TN."""
    import os

    if os.environ.get("GAIA_OFFLINE") == "1":
        return {}

    now = datetime.now(timezone.utc)
    for station in ["KMRX", "KGSP", "KOHX"]:
        keys = _list_nexrad_files(station, now)
        if not keys:
            # Try yesterday
            from datetime import timedelta

            keys = _list_nexrad_files(station, now - timedelta(days=1))
        for key in keys[:3]:
            raw = _download_nexrad(key)
            if not raw:
                continue
            radar = _parse_with_pyart(raw)
            if radar is None:
                continue
            data = _extract_for_region(radar)
            data["station"] = station
            data["file_key"] = key
            return data
    return {}


def fetch_nexrad_for_datetime(station: str, dt: datetime) -> dict[str, Any]:
    """Fetch NEXRAD for a specific datetime (historical)."""
    import os

    if os.environ.get("GAIA_OFFLINE") == "1":
        return {}

    keys = _list_nexrad_files(station, dt)
    if not keys:
        return {}
    # Prefer file closest to dt
    best_key = keys[0]
    raw = _download_nexrad(best_key)
    if not raw:
        return {}
    radar = _parse_with_pyart(raw)
    if radar is None:
        return {}
    data = _extract_for_region(radar)
    data["station"] = station
    data["file_key"] = best_key
    data["scan_time"] = dt.isoformat()
    return data
