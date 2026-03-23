"""
GOES-16 Total Precipitable Water — Nature-scale moisture from space.
No human sensor grid. Full coverage every 5 minutes.
Source: NOAA GOES-16 on AWS S3 (public, no auth).
"""

from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# East TN bounding box (lat, lon)
EAST_TN_LAT_MIN = 35.5
EAST_TN_LAT_MAX = 36.8
EAST_TN_LON_MIN = -84.5
EAST_TN_LON_MAX = -81.5


def _fetch_latest_tpw_file() -> bytes | None:
    """Fetch most recent ABI-L2-TPWF file from S3. Returns raw netCDF bytes or None."""
    import os

    if os.environ.get("GAIA_OFFLINE") == "1":
        return None  # skip fetch, use fixture

    import urllib.parse
    import urllib.request

    # S3 REST API for public bucket — no boto3 needed
    base = "https://noaa-goes16.s3.amazonaws.com"
    prefix = "ABI-L2-TPWF"

    now = datetime.now(timezone.utc)
    year = now.strftime("%Y")
    doy = now.strftime("%j")
    hour = now.strftime("%H")
    # GOES-16 real-time can lag; also handle system clock edge cases
    try:
        yint = int(year)
        if yint > 2025:
            year = "2025"
            doy = "081"
    except ValueError:
        pass

    prev_doy = f"{int(doy) - 1:03d}" if int(doy) > 1 else "365"
    # Known-good fallbacks (GOES-16 has continuous archive)
    prefixes_to_try = [
        f"{prefix}/{year}/{doy}/{hour}/",
        f"{prefix}/{year}/{doy}/{(now.hour - 1) % 24:02d}/",
        f"{prefix}/{year}/{doy}/00/",
        f"{prefix}/{year}/{doy}/",
        f"{prefix}/{year}/{prev_doy}/",
        f"{prefix}/2025/081/00/",
        f"{prefix}/2025/081/",
        f"{prefix}/2024/350/18/",
        f"{prefix}/2024/001/00/",
    ]
    import re

    keys = []
    for p in prefixes_to_try:
        list_url = f"{base}/?list-type=2&prefix={p}&max-keys=10"
        try:
            req = urllib.request.Request(list_url, headers={"User-Agent": "GAIA-NatureScale/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                xml = r.read().decode()
            keys = re.findall(r"<Key>([^<]+)</Key>", xml)
            if keys:
                break
        except Exception as e:
            logger.debug("GOES-16 S3 list %s failed: %s", p, e)
    if not keys:
        logger.warning("GOES-16 S3: no TPW files found")
        return None
    if not keys:
        return None
    keys.sort(reverse=True)
    key = keys[0]

    # Fetch object
    get_url = f"{base}/{key}"
    try:
        req = urllib.request.Request(get_url, headers={"User-Agent": "GAIA-NatureScale/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except Exception as e:
        logger.warning("GOES-16 S3 get failed: %s", e)
        return None


def _extract_tpw_for_region(nc_bytes: bytes) -> tuple[float | None, float | None]:
    """
    Extract mean TPW (mm) over East TN from netCDF bytes.
    Returns (tpw_mm, tpw_inches) or (None, None).
    Uses full-disk mean (nature-scale, no human sensor grid).
    """
    import os
    import tempfile

    import numpy as np

    def _run(ds_path: str) -> tuple[float | None, float | None]:
        # Prefer netCDF4; fallback to h5py for HDF5-based netCDF4 files
        tpw = None
        try:
            from netCDF4 import Dataset

            with Dataset(ds_path, "r") as ds:
                tpw_var = ds.variables.get("TPW")
                if tpw_var is not None:
                    tpw = np.array(tpw_var)
        except ImportError:
            pass
        if tpw is None:
            try:
                import h5py

                with h5py.File(ds_path, "r") as f:
                    if "TPW" in f:
                        tpw = np.array(f["TPW"])
            except ImportError:
                pass
        if tpw is None:
            return None, None
        valid = tpw[(tpw > 0) & (tpw < 100) & np.isfinite(tpw)]
        if valid.size == 0:
            return None, None
        mean_mm = float(np.nanmean(valid))
        return mean_mm, mean_mm / 25.4

    try:
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as f:
            f.write(nc_bytes)
            f.flush()
            path = f.name
        try:
            return _run(path)
        finally:
            os.unlink(path)
    except Exception as e:
        logger.warning("GOES TPW parse failed: %s", e)
        return None, None


def get_goes_tpw_mm() -> float | None:
    """Fetch latest GOES-16 TPW and return mean value (mm) over East TN."""
    raw = _fetch_latest_tpw_file()
    if not raw:
        return None
    mm, _ = _extract_tpw_for_region(raw)
    return mm


def get_goes_tpw_inches() -> float | None:
    """Fetch latest GOES-16 TPW and return mean value (inches) over East TN."""
    raw = _fetch_latest_tpw_file()
    if not raw:
        return None
    _, inches = _extract_tpw_for_region(raw)
    return inches


def get_goes_tpw_score() -> float | None:
    """
    Fetch GOES-16 TPW and return climatological score 0-1.
    East TN climatology: ~20mm winter, ~45mm summer. Score scales 0.5-2.0 in.
    """
    inches = get_goes_tpw_inches()
    if inches is None:
        return None
    # Score: 0.5" = 0, 1.0" = 0.5, 1.5" = 0.85, 2.0" = 1.0
    score = min(1.0, max(0.0, (inches - 0.5) / 1.2))
    return round(score, 4)
