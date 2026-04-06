#!/usr/bin/env python3
from __future__ import annotations

import gzip
import os
import shutil
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import rasterio
from rasterio.windows import Window


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_LAT = 35.97
PILOT_LON = -82.10
USER_AGENT = "HollerSiren/1.0"

# Keep total worst-case latency bounded for HTTP handlers (e.g. gunicorn ~30s).
# Previously each candidate used timeout=20s and the list was long enough to exceed worker limits.
HTTP_TIMEOUT_SEC = float(os.environ.get("GAIA_LIVE_RAIN_HTTP_TIMEOUT", "3"))
MAX_STAGE4_ATTEMPTS = int(os.environ.get("GAIA_LIVE_RAIN_MAX_STAGE4", "6"))
MAX_MRMS_ATTEMPTS = int(os.environ.get("GAIA_LIVE_RAIN_MAX_MRMS", "2"))


def _read_stage4_tif(data: bytes, lat: float, lon: float, kind: str) -> float:
    tmp = Path("/tmp/stage4_live.tif")
    tmp.write_bytes(data)
    with rasterio.open(tmp) as src:
        row, col = src.index(lon, lat)
        window = Window(max(0, col - 2), max(0, row - 2), 5, 5)
        vals = src.read(1, window=window).astype(float)
        valid = vals[vals > 0]
        rain = float(valid.mean()) / 100.0 if valid.size else 0.0
        return rain / 24.0 if kind == "daily" else rain


def _read_mrms_grib(data: bytes, lat: float, lon: float) -> float:
    gz_path = Path("/tmp/mrms_live.grib2.gz")
    grib_path = Path("/tmp/mrms_live.grib2")
    gz_path.write_bytes(data)
    with gzip.open(gz_path, "rb") as src, grib_path.open("wb") as dst:
        shutil.copyfileobj(src, dst)
    with rasterio.open(grib_path) as ds:
        row, col = ds.index(lon, lat)
        window = Window(max(0, col - 2), max(0, row - 2), 5, 5)
        vals = ds.read(1, window=window).astype(float)
        valid = vals[vals >= 0]
        return float(valid.mean()) if valid.size else 0.0


def get_current_rainfall_noaa(lat: float = PILOT_LAT, lon: float = PILOT_LON) -> tuple[float, str]:
    now = datetime.now(timezone.utc)
    candidates = []
    for h in range(1, 7):
        dt = now - timedelta(hours=h)
        ds = dt.strftime("%Y%m%d")
        hr = dt.strftime("%H")
        candidates.append((
            f"https://water.noaa.gov/resources/downloads/precip/stageIV/current/"
            f"nws_precip_last01h_{ds}_{hr}_conus.tif",
            "stage4-hourly",
        ))
        candidates.append((
            f"https://water.noaa.gov/resources/downloads/precip/stageIV/current/"
            f"nws_precip_last01h_{ds}{hr}_conus.tif",
            "stage4-hourly-legacy",
        ))
    for dback in range(0, 5):
        dt = now - timedelta(days=dback)
        y, m, d = dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")
        ds = dt.strftime("%Y%m%d")
        candidates.append((
            f"https://water.noaa.gov/resources/downloads/precip/{y}/{m}/{d}/"
            f"nws_precip_1day_{ds}_conus.tif",
            "stage4-daily",
        ))

    stage4_tries = 0
    for url, kind in candidates:
        if stage4_tries >= MAX_STAGE4_ATTEMPTS:
            break
        stage4_tries += 1
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SEC) as resp:
                data = resp.read()
            if len(data) < 1000:
                continue
            return _read_stage4_tif(data, lat, lon, "daily" if kind == "stage4-daily" else "hourly"), f"{kind}:{url[-48:]}"
        except Exception:
            continue

    mrms_candidates = [
        "https://mrms.ncep.noaa.gov/data/2D/PrecipRate/MRMS_PrecipRate.latest.grib2.gz",
    ]
    for h in range(0, 6):
        dt = now - timedelta(hours=h)
        stamp = dt.strftime("%Y%m%d-%H%M00")
        mrms_candidates.append(
            f"https://mrms.ncep.noaa.gov/data/2D/PrecipRate/MRMS_PrecipRate_00.00_{stamp}.grib2.gz"
        )

    mrms_tries = 0
    for url in mrms_candidates:
        if mrms_tries >= MAX_MRMS_ATTEMPTS:
            break
        mrms_tries += 1
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SEC) as resp:
                data = resp.read()
            if len(data) < 1000:
                continue
            return _read_mrms_grib(data, lat, lon), f"mrms:{url.split('/')[-1]}"
        except Exception:
            continue

    return 0.0, "no_data"


if __name__ == "__main__":
    rain, src = get_current_rainfall_noaa()
    print(f"Current rainfall: {rain:.4f} mm/hr")
    print(f"Source: {src}")
