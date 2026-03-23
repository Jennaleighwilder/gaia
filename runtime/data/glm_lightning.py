"""
GOES-16 GLM Lightning — Nature-scale convection detection.
Source: s3://noaa-goes16/GLM-L2-LCFA/
Flash rate > 10/min = active convection, > 50/min = intense.
"""

from __future__ import annotations

import io
import logging
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

EAST_TN_LAT = (35.5, 36.8)
EAST_TN_LON = (-84.5, -81.5)
BASE = "https://noaa-goes16.s3.amazonaws.com"
PREFIX = "GLM-L2-LCFA"


def _list_glm_files(dt: datetime) -> list[str]:
    """List GLM LCFA files for given datetime. Returns sorted keys (newest first)."""
    year = dt.strftime("%Y")
    doy = dt.strftime("%j")
    hour = dt.strftime("%H")
    prefix = f"{PREFIX}/{year}/{doy}/{hour}/"
    url = f"{BASE}/?list-type=2&prefix={urllib.parse.quote(prefix)}&max-keys=50"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA-NatureScale/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            xml = r.read().decode()
    except Exception as e:
        logger.warning("GLM S3 list failed: %s", e)
        return []
    keys = re.findall(r"<Key>([^<]+)</Key>", xml)
    keys.sort(reverse=True)
    return keys


def _download_glm(key: str) -> bytes | None:
    url = f"{BASE}/{urllib.parse.quote(key)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA-NatureScale/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except Exception as e:
        logger.warning("GLM S3 get failed: %s", e)
        return None


def _count_flashes_in_region(raw: bytes) -> tuple[int, float]:
    """
    Parse GLM netCDF and count flashes in East TN box.
    Returns (flash_count, total_energy_j).
    """
    try:
        try:
            import xarray as xr
            ds = xr.open_dataset(io.BytesIO(raw))
        except ImportError:
            import netCDF4
            ds = netCDF4.Dataset(io.BytesIO(raw), "r")
    except ImportError:
        logger.warning("netCDF4 or xarray required for GLM")
        return 0, 0.0
    except Exception as e:
        logger.warning("GLM parse failed: %s", e)
        return 0, 0.0
    try:
        # GLM LCFA: flash_centroid_latitude, flash_centroid_longitude, flash_energy
        lat = ds.variables.get("flash_centroid_lat") or ds.variables.get("flash_lat") or ds.variables.get("flash_centroid_latitude")
        lon = ds.variables.get("flash_centroid_lon") or ds.variables.get("flash_lon") or ds.variables.get("flash_centroid_longitude")
        energy = ds.variables.get("flash_energy", None)
        if lat is None or lon is None:
            for v in list(ds.variables.keys()):
                if "lat" in v.lower() and "centroid" in v.lower():
                    lat = ds.variables[v]
                    break
            if lat is None:
                for v in list(ds.variables.keys()):
                    if "lat" in v.lower():
                        lat = ds.variables[v]
                        break
            if lon is None:
                for v in list(ds.variables.keys()):
                    if "lon" in v.lower():
                        lon = ds.variables[v]
                        break
        if lat is None or lon is None:
            return 0, 0.0
        lats = lat[:] if hasattr(lat, "__getitem__") else lat
        lons = lon[:] if hasattr(lon, "__getitem__") else lon
        mask = (
            (lats >= EAST_TN_LAT[0]) & (lats <= EAST_TN_LAT[1])
            & (lons >= EAST_TN_LON[0]) & (lons <= EAST_TN_LON[1])
        )
        count = int(mask.sum()) if hasattr(mask, "sum") else 0
        e_tot = 0.0
        if energy is not None:
            try:
                e_arr = energy[:]
                if hasattr(mask, "__array__"):
                    e_tot = float((e_arr[mask]).sum())
                else:
                    e_tot = float(e_arr.sum())
            except Exception:
                pass
        if hasattr(ds, "close"):
            ds.close()
        return count, e_tot
    except Exception as e:
        logger.warning("GLM parse failed: %s", e)
        return 0, 0.0


def fetch_glm_flash_stats(dt: datetime | None = None) -> dict:
    """
    Fetch GLM data for dt (default: now) and return flash stats.
    Returns: {flash_count, energy_j, flash_rate_per_min, available}
    """
    import os

    if os.environ.get("GAIA_OFFLINE") == "1":
        return {"flash_count": 0, "energy_j": 0.0, "flash_rate_per_min": 0.0, "available": False}

    dt = dt or datetime.now(timezone.utc)
    keys = _list_glm_files(dt)
    if not keys:
        keys = _list_glm_files(dt - timedelta(hours=1))
    for key in keys[:3]:
        raw = _download_glm(key)
        if not raw:
            continue
        count, energy = _count_flashes_in_region(raw)
        # Assume ~5 min window per file
        rate = count / 5.0 if count else 0.0
        return {
            "flash_count": count,
            "energy_j": round(energy, 2),
            "flash_rate_per_min": round(rate, 2),
            "available": True,
        }
    return {"flash_count": 0, "energy_j": 0.0, "flash_rate_per_min": 0.0, "available": False}
