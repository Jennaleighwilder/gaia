"""
Weekly Gulf of Mexico OISST anomaly (NOAA ERDDAP), lazy per-ISO-week cache.
Avoids downloading full 1981–present in one pass.
"""

from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache" / "gulf_weekly"
ERDDAP_JSON = (
    "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg_LonPM180.json"
)


def _iso_week_key(d: datetime) -> tuple[int, int]:
    t = d.date().isocalendar()
    return int(t[0]), int(t[1])


def _mean_anom_from_erddap(payload: dict) -> float | None:
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
    return float(np.mean(vals))


class WeeklyOISSTArchive:
    def __init__(self, *, use_network: bool = True) -> None:
        self.use_network = use_network
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, iso_year: int, iso_week: int) -> Path:
        return CACHE_DIR / f"gulf_{iso_year}_W{iso_week:02d}.json"

    def get_week_anomaly(self, iso_year: int, iso_week: int) -> dict[str, float | bool | str]:
        p = self._cache_path(iso_year, iso_week)
        if p.exists():
            try:
                return json.loads(p.read_text())
            except json.JSONDecodeError:
                pass

        if not self.use_network:
            return {"anomaly": 0.0, "warm_pulse": False, "very_warm": False, "source": "offline"}

        try:
            monday = datetime.fromisocalendar(iso_year, iso_week, 1)
        except ValueError:
            return {"anomaly": 0.0, "warm_pulse": False, "very_warm": False, "source": "bad_week"}

        ts = monday.strftime("%Y-%m-%dT12:00:00Z")
        url = (
            f"{ERDDAP_JSON}?anom[({ts}):1:({ts})]"
            "[(0.0):1:(0.0)][(23):1:(30)][(-98):1:(-82)]"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0 (research)"})
            with urllib.request.urlopen(req, timeout=45) as r:
                payload = json.loads(r.read().decode("utf-8", errors="replace"))
            mean_anom = _mean_anom_from_erddap(payload)
            if mean_anom is None:
                raise ValueError("empty anomaly")
            rec = {
                "anomaly": round(mean_anom, 3),
                "warm_pulse": bool(mean_anom > 0.5),
                "very_warm": bool(mean_anom > 1.0),
                "week_start": monday.strftime("%Y-%m-%d"),
                "source": "noaa_oisst_erddap",
            }
            p.write_text(json.dumps(rec))
            time.sleep(0.12)
            return rec
        except Exception as e:
            return {
                "anomaly": 0.0,
                "warm_pulse": False,
                "very_warm": False,
                "source": f"err:{e!s}"[:60],
            }

    def get_pre_outbreak_gulf_features(
        self, outbreak_date: datetime, _archive: dict | None = None
    ) -> dict[str, float | int]:
        """
        Five ISO weeks strictly before outbreak_date's week: weeks_back 1..5
        (each step = 7 days back from previous anchor).
        """
        anom_vals: list[float] = []
        t = outbreak_date
        for _ in range(5):
            t = t - timedelta(weeks=1)
            iy, iw = _iso_week_key(t)
            rec = self.get_week_anomaly(iy, iw)
            anom_vals.append(float(rec.get("anomaly", 0.0)))

        if not anom_vals:
            return {
                "gulf_max_anom_5wk": 0.0,
                "gulf_mean_anom_5wk": 0.0,
                "gulf_warm_pulse_5wk": 0,
                "gulf_warming_trend": 0.0,
            }

        return {
            "gulf_max_anom_5wk": float(max(anom_vals)),
            "gulf_mean_anom_5wk": float(np.mean(anom_vals)),
            "gulf_warm_pulse_5wk": int(max(anom_vals) > 0.5),
            "gulf_warming_trend": float(anom_vals[0] - anom_vals[-1]) if len(anom_vals) >= 3 else 0.0,
        }
