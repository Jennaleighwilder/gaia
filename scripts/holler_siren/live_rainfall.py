#!/usr/bin/env python3
from __future__ import annotations

import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import rasterio
from rasterio.warp import transform
from rasterio.windows import Window


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_LAT = 35.97
PILOT_LON = -82.10
USER_AGENT = "HollerSiren/1.0"


def get_current_rainfall_noaa(lat: float = PILOT_LAT, lon: float = PILOT_LON) -> tuple[float | None, str]:
    now = datetime.now(timezone.utc)
    check_dt = now - timedelta(hours=2)
    date_str = check_dt.strftime("%Y%m%d")
    hour_str = check_dt.strftime("%H")
    url = (
        "https://water.noaa.gov/resources/downloads/precip/stageIV/current/"
        f"nws_precip_last01h_{date_str}{hour_str}_conus.tif"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        if len(data) < 1000:
            return 0.0, url
        tmp = Path("/tmp/stage4_live.tif")
        tmp.write_bytes(data)
        with rasterio.open(tmp) as src:
            x, y = transform("EPSG:4326", src.crs, [lon], [lat])
            row, col = src.index(x[0], y[0])
            window = Window(max(0, col - 2), max(0, row - 2), 5, 5)
            vals = src.read(1, window=window).astype(float)
            valid = vals[vals > 0]
            if valid.size == 0:
                return 0.0, url
            return float(valid.mean()), url
    except Exception as exc:
        return None, str(exc)


def main() -> int:
    print("=== STEP 5: LIVE NOAA RAINFALL FEED ===")
    rain, source = get_current_rainfall_noaa()
    print(f"Current hourly rainfall at pilot area: {rain} mm")
    print(f"Source: {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
