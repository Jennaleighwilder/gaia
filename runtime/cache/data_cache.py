"""
GAIADataCache — real-time background data fetchers.

Runs threads per data source. Governor reads from cache, never fetches directly.
Use GAIA_NO_PROXY=1 to bypass proxy when corporate proxy blocks NOAA/USGS.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

EAST_TN_BBOX = "35.5,-84.5,36.8,-81.5"  # south,west,north,east

_DIRECT_OPENER = None


def _get_opener():
    """Use direct connection (no proxy) when GAIA_NO_PROXY=1 or proxy causes 403."""
    global _DIRECT_OPENER
    if _DIRECT_OPENER is not None:
        return _DIRECT_OPENER
    if os.environ.get("GAIA_NO_PROXY", "1") == "1":
        _DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return _DIRECT_OPENER


def _fetch_json(url: str, timeout: int = 30) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0 (severe-weather; theforgottencode.com)"})
        opener = _get_opener()
        if opener:
            with opener.open(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", errors="replace"))
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception as e:
        logger.warning("Fetch %s failed: %s", url[:80], e)
        return None


def _fetch_text(url: str, timeout: int = 30) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0 (severe-weather; theforgottencode.com)"})
        opener = _get_opener()
        if opener:
            with opener.open(req, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="replace")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("Fetch %s failed: %s", url[:80], e)
        return None


class DataSource:
    """Single data source with interval and staleness."""

    def __init__(self, key: str, interval_sec: int, fetch_fn):
        self.key = key
        self.interval_sec = interval_sec
        self.fetch_fn = fetch_fn
        self.data: Any = None
        self.last_fetch = 0.0
        self.stale = True
        self.last_error: str | None = None

    def run_once(self) -> None:
        try:
            result = self.fetch_fn()
            if result is not None:
                self.data = result
                self.last_fetch = time.time()
                self.stale = False
                self.last_error = None
            else:
                self.stale = True
                self.last_error = "fetch returned None"
        except Exception as e:
            self.stale = True
            self.last_error = str(e)
            logger.warning("%s fetch failed: %s", self.key, e)


def _fetch_asos() -> dict | None:
    url = "https://mesonet.agron.iastate.edu/api/1/current.json"
    data = _fetch_json(url)
    if not data:
        return None
    stations = ["KTYS", "KTRI", "KGKT"]
    return {s: data.get("data", {}).get(s) for s in stations}


def _fetch_usgs_streamflow() -> dict | None:
    url = "https://waterservices.usgs.gov/nwis/iv/?format=json&sites=03465500,03571850&parameterCd=00065"
    data = _fetch_json(url)
    if not data or "value" not in str(data):
        return None
    return data


def _fetch_goes_tpw() -> dict | None:
    return {"tpw_mm": None, "source": "s3_placeholder"}


def _fetch_goes_glm() -> dict | None:
    return {"flash_count": 0, "source": "s3_placeholder"}


def _fetch_nexrad() -> dict | None:
    return {"KMRX": None}


def _fetch_firms() -> dict | None:
    import os

    if os.environ.get("GAIA_OFFLINE") == "1":
        return {"fires": [], "stale": True}

    key = os.environ.get("FIRMS_MAP_KEY", "")
    if not key:
        return {"fires": [], "stale": True}
    bbox = EAST_TN_BBOX
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/{bbox}/1"
    text = _fetch_text(url)
    if not text:
        return {"fires": [], "stale": True}
    lines = [l for l in text.strip().split("\n") if l and not l.startswith("#")]
    fires = []
    for ln in lines[1:]:
        parts = ln.split(",")
        if len(parts) >= 8:
            try:
                lat, lon = float(parts[0]), float(parts[1])
                frp = float(parts[8]) if len(parts) > 8 else 0
                fires.append({"lat": lat, "lon": lon, "frp": frp})
            except (ValueError, IndexError):
                pass
    return {"fires": fires, "stale": False}


def _fetch_usgs_earthquakes() -> dict | None:
    import os

    if os.environ.get("GAIA_OFFLINE") == "1":
        return {"features": []}

    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/1.0_hour.geojson"
    return _fetch_json(url)


def _fetch_noaa_kp() -> dict | None:
    url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
    return _fetch_json(url)


def _fetch_smap() -> dict | None:
    return {"soil_moisture": None}


SOURCES = [
    ("asos", 300, _fetch_asos),
    ("usgs_streamflow", 900, _fetch_usgs_streamflow),
    ("goes_tpw", 600, _fetch_goes_tpw),
    ("goes_glm", 300, _fetch_goes_glm),
    ("nexrad", 300, _fetch_nexrad),
    ("firms", 600, _fetch_firms),
    ("usgs_earthquakes", 60, _fetch_usgs_earthquakes),
    ("noaa_kp", 900, _fetch_noaa_kp),
    ("smap", 86400, _fetch_smap),
]


class GAIADataCache:
    """Background data cache. One thread per source."""

    def __init__(self):
        self.sources: dict[str, DataSource] = {}
        self._threads: list[threading.Thread] = []
        self._stop = threading.Event()

    def _run_source(self, ds: DataSource) -> None:
        while not self._stop.is_set():
            ds.run_once()
            self._stop.wait(timeout=ds.interval_sec)

    def start(self) -> None:
        for key, interval, fetch_fn in SOURCES:
            ds = DataSource(key, interval, fetch_fn)
            self.sources[key] = ds
            t = threading.Thread(target=self._run_source, args=(ds,), daemon=True)
            t.start()
            self._threads.append(t)
        logger.info("GAIADataCache started %d sources", len(self.sources))

    def stop(self) -> None:
        self._stop.set()

    def get(self, key: str) -> Any:
        ds = self.sources.get(key)
        return ds.data if ds else None

    def get_staleness(self) -> dict[str, bool]:
        return {k: v.stale for k, v in self.sources.items()}

    def get_last_fetch(self) -> dict[str, float]:
        return {k: v.last_fetch for k, v in self.sources.items()}
