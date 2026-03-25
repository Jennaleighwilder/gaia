"""
NEXRAD Level II Radar — Nature-scale rotation detection.
Source: AWS S3 unidata-nexrad-level2 (public HTTP via urllib; no boto3/S3 SDK).
Primary: KMRX (Morristown TN) — covers all East TN.
"""

from __future__ import annotations

import gzip
import io
import logging
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

BASE_URL = "https://unidata-nexrad-level2.s3.amazonaws.com"

# Default region when station unknown (East TN monitoring).
_DEFAULT_REGION_BBOX: tuple[float, float, float, float] = (35.5, 36.8, -84.5, -81.5)
EAST_TN_LAT = (_DEFAULT_REGION_BBOX[0], _DEFAULT_REGION_BBOX[1])
EAST_TN_LON = (_DEFAULT_REGION_BBOX[2], _DEFAULT_REGION_BBOX[3])

# (lat_min, lat_max, lon_min, lon_max) — analysis window for each radar’s own coverage, not the county under watch.
STATION_BBOX: dict[str, tuple[float, float, float, float]] = {
    "KMRX": (35.5, 36.8, -84.5, -81.5),  # East TN
    "KTLX": (34.5, 36.5, -99.0, -96.0),  # Oklahoma
    "KGSP": (34.0, 36.0, -82.5, -80.0),  # Carolinas
    "KOHX": (35.5, 37.5, -87.5, -85.0),  # Middle TN
    "KFCX": (36.0, 38.0, -81.5, -79.0),  # SW Virginia
    "KVTX": (32.0, 36.5, -120.0, -116.0),
    "KAMX": (24.5, 27.5, -81.5, -79.5),
    "KLOT": (40.5, 43.5, -89.5, -86.0),
    "KATX": (46.0, 50.0, -125.0, -121.0),
}


def get_station_bbox(station: str) -> tuple[float, float, float, float]:
    """Return (lat_min, lat_max, lon_min, lon_max) for station; default East TN if unknown."""
    return STATION_BBOX.get(station.strip().upper(), _DEFAULT_REGION_BBOX)

_NEXRAD_OPENER: urllib.request.OpenerDirector | None = None


def _nexrad_opener() -> urllib.request.OpenerDirector | None:
    """Match data_cache: GAIA_NO_PROXY=1 uses direct HTTPS (no corporate proxy / 403 on S3)."""
    global _NEXRAD_OPENER
    if _NEXRAD_OPENER is not None:
        return _NEXRAD_OPENER
    if os.environ.get("GAIA_NO_PROXY", "1") == "1":
        _NEXRAD_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return _NEXRAD_OPENER


def _urlopen_nexrad(req: urllib.request.Request, timeout: float):
    opener = _nexrad_opener()
    if opener is not None:
        return opener.open(req, timeout=timeout)
    return urllib.request.urlopen(req, timeout=timeout)


def _list_nexrad_files(station: str, dt: datetime) -> list[str]:
    """List NEXRAD files for station on date. Returns sorted keys (newest first)."""
    y, m, d = dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")
    prefix = f"{y}/{m}/{d}/{station}/"
    # Public ListObjectsV2 (list-type=2); no SDK.
    q = urllib.parse.urlencode(
        {"list-type": "2", "prefix": prefix, "max-keys": "100"}
    )
    url = f"{BASE_URL}/?{q}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
        with _urlopen_nexrad(req, 15) as r:
            xml = r.read().decode()
    except Exception as e:
        logger.warning("NEXRAD HTTP list failed: %s", e)
        return []
    keys = re.findall(r"<Key>([^<]+)</Key>", xml)
    keys.sort(reverse=True)
    return keys


def _download_nexrad(key: str) -> bytes | None:
    """Download single NEXRAD file, return raw bytes (gunzipped if .gz)."""
    url = f"{BASE_URL}/{urllib.parse.quote(key, safe='/')}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
        with _urlopen_nexrad(req, 120) as r:
            raw = r.read()
    except Exception as e:
        logger.warning("NEXRAD HTTP get failed: %s", e)
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


def _extract_for_box(
    radar: Any,
    lat_box: tuple[float, float] | None = None,
    lon_box: tuple[float, float] | None = None,
    *,
    station: str | None = None,
) -> dict[str, float | None]:
    """
    Extract composite reflectivity, velocity, VIL for a lat/lon box.
    If lat_box/lon_box omitted, uses get_station_bbox(station) when station is set,
    else East TN default.

    Rotation couplet: per-sweep span (inbound + outbound) in knots, after rejecting
    sweeps where both extrema sit at Nyquist (ambiguous / folded — not a mesocyclone).
    Never merges max(+vel) from one tilt with min(-vel) from another.
    """
    import numpy as np

    if lat_box is not None and lon_box is not None:
        lat_min, lat_max = lat_box
        lon_min, lon_max = lon_box
    elif station:
        lat_min, lat_max, lon_min, lon_max = get_station_bbox(station)
    else:
        lat_min, lat_max = EAST_TN_LAT
        lon_min, lon_max = EAST_TN_LON
    out = {
        "composite_reflectivity": None,
        "velocity_max": None,
        "velocity_min": None,
        "vil": None,
        "echo_top_km": None,
        "rotation_couplet_kt": None,
    }
    all_refl = []
    # (couplet_kt, vmax_mps, vmin_mps) per sweep — only trustworthy rows
    per_sweep: list[tuple[float, float, float]] = []
    NYQ_FRAC = 0.88
    MIN_VEL_GATES = 50

    try:
        nsweeps = radar.nsweeps
        for sw in range(nsweeps):
            gate_lat, gate_lon, _ = radar.get_gate_lat_lon_alt(sw)
            mask = (
                (gate_lat >= lat_min)
                & (gate_lat <= lat_max)
                & (gate_lon >= lon_min)
                & (gate_lon <= lon_max)
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
            if "velocity" not in radar.fields:
                continue
            vel = radar.fields["velocity"]["data"][sweep_slice]
            vel_m = np.ma.masked_invalid(vel)
            vel_m = np.ma.masked_where(np.abs(vel_m) > 200, vel_m)
            m = np.ma.masked_where(~mask, vel_m)
            if np.ma.count(m) < MIN_VEL_GATES:
                continue
            vmax_s = float(np.ma.max(m))
            vmin_s = float(np.ma.min(m))
            # Need a signed dipole in-bounds (not uniform sign noise).
            if vmax_s <= 0 or vmin_s >= 0:
                continue
            nyq_mps: float | None = None
            try:
                nyq_mps = float(radar.get_nyquist_vel(sweep=sw))
            except Exception:
                pass
            if (
                nyq_mps is not None
                and nyq_mps > 0
                and vmax_s >= NYQ_FRAC * nyq_mps
                and vmin_s <= -NYQ_FRAC * nyq_mps
            ):
                # Both limbs pegged at Nyquist — range in domain, not a resolved couplet.
                continue
            span_kt = (abs(vmax_s) + abs(vmin_s)) * 1.944
            per_sweep.append((span_kt, vmax_s, vmin_s))

        if all_refl:
            out["composite_reflectivity"] = float(max(all_refl))
        if per_sweep:
            per_sweep.sort(key=lambda t: t[0])
            mid = len(per_sweep) // 2
            ck, vmax_m, vmin_m = per_sweep[mid]
            out["rotation_couplet_kt"] = float(ck)
            out["velocity_max"] = float(vmax_m)
            out["velocity_min"] = float(vmin_m)

    except Exception as e:
        logger.warning("NEXRAD region extract failed: %s", e)
    return out


def _extract_for_region(radar: Any, station: str | None = None) -> dict[str, float | None]:
    """Extract using station coverage bbox (default region if station omitted)."""
    return _extract_for_box(radar, station=station)


ASOS_TO_NEXRAD: dict[str, str] = {
    "KOKC": "KTLX", "KLAX": "KVTX", "KMIA": "KAMX",
    "KORD": "KLOT", "KSEA": "KATX",
}


def fetch_latest_for_station(
    station: str,
    lat_box: tuple[float, float] | None = None,
    lon_box: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Fetch most recent NEXRAD for station. Uses get_station_bbox when box not given."""
    import os
    from datetime import timedelta

    if os.environ.get("GAIA_OFFLINE") == "1":
        return {}
    if lat_box is None or lon_box is None:
        bb = get_station_bbox(station)
        lat_box = lat_box or (bb[0], bb[1])
        lon_box = lon_box or (bb[2], bb[3])
    now = datetime.now(timezone.utc)
    keys = _list_nexrad_files(station, now)
    if not keys:
        keys = _list_nexrad_files(station, now - timedelta(days=1))
    for key in keys[:3]:
        raw = _download_nexrad(key)
        if not raw:
            continue
        radar = _parse_with_pyart(raw)
        if radar is None:
            continue
        data = _extract_for_box(radar, lat_box, lon_box, station=station)
        data["station"] = station
        data["file_key"] = key
        data["parse_success"] = True
        data["rotation_score"] = detect_velocity_couplet(data)
        return data
    return {}


def detect_velocity_couplet(velocity_data: dict) -> float:
    """
    Score 0-1 from velocity couplet magnitude (kt).
    >90 kt = 1.0, 50-90 = 0.7, 30-50 = 0.5, <30 = proportional.
    Missing or uncertain couplet → 0.0 (never treat unknown as tornadic).
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
            data = _extract_for_box(radar, station=station)
            data["station"] = station
            data["file_key"] = key
            data["parse_success"] = True
            data["rotation_score"] = detect_velocity_couplet(data)
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
    data = _extract_for_box(radar, station=station)
    data["station"] = station
    data["file_key"] = best_key
    data["scan_time"] = dt.isoformat()
    data["parse_success"] = True
    data["rotation_score"] = detect_velocity_couplet(data)
    return data
