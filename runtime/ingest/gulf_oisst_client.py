"""
NOAA OISST v2.1 daily anomaly (ERDDAP) — Gulf box mean, lon −180..180 dataset.
Uses precomputed `anom` (NCEI analysis vs its climatology).
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache" / "gulf_oisst"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ERDDAP_JSON = (
    "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg_LonPM180.json"
)


def _mean_anom_from_json(payload: dict) -> float | None:
    rows = payload.get("table", {}).get("rows", [])
    if not rows:
        return None
    vals: list[float] = []
    for row in rows[1:]:
        if not row:
            continue
        x = row[-1]
        if x is None:
            continue
        try:
            v = float(x)
            if -12 < v < 12:
                vals.append(v)
        except (TypeError, ValueError):
            continue
    if not vals:
        return None
    return sum(vals) / len(vals)


class GulfOISSTClient:
    def __init__(self, *, use_network: bool = True) -> None:
        self.use_network = use_network

    def get_gulf_sst_anomaly(self, year: int, month: int, day: int = 15) -> dict:
        cache = CACHE_DIR / f"gulf_{year}_{month:02d}_{day:02d}.json"
        if cache.exists():
            try:
                return json.loads(cache.read_text())
            except json.JSONDecodeError:
                pass

        if not self.use_network:
            return {
                "gulf_oisst_anomaly": 0.0,
                "gulf_oisst_warm_pulse": False,
                "source": "offline_no_cache",
            }

        ts = f"{year}-{month:02d}-{day:02d}T12:00:00Z"
        url = (
            f"{ERDDAP_JSON}?anom[({ts}):1:({ts})]"
            "[(0.0):1:(0.0)][(23):1:(30)][(-98):1:(-82)]"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0 (research)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                payload = json.loads(r.read().decode("utf-8", errors="replace"))
            anom = _mean_anom_from_json(payload)
            if anom is None:
                raise ValueError("no anomaly values in ERDDAP response")
            warm = bool(anom > 0.5)
            result = {
                "gulf_oisst_anomaly": round(anom, 3),
                "gulf_oisst_warm_pulse": warm,
                "source": "noaa_oisst_erddap",
            }
            cache.write_text(json.dumps(result))
            return result
        except Exception as e:
            return {
                "gulf_oisst_anomaly": 0.0,
                "gulf_oisst_warm_pulse": False,
                "source": f"unavailable:{e!s}"[:80],
            }
