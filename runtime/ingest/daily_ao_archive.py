"""
Daily AO for pre-outbreak windows.

Primary: NOAA CPC ASCII (single file). If that URL fails (404 / network),
next: merged ERA5-based daily AO at `data/cache/era5_daily_ao/daily_ao_archive.json`
(see `runtime/ingest/era5_daily_ao.py` and `scripts/cds_connection_test.py`).
Final fallback: linear interpolation between **15th-of-month** values from
`data/global_indices/ao_monthly.dat` (NOT true daily AO — trends/plunges are smoothed).
"""

from __future__ import annotations

import calendar
import json
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from runtime.ingest.era5_daily_ao import ERA5_DAILY_AO_ARCHIVE_PATH, load_era5_daily_ao_archive

ROOT = Path(__file__).resolve().parents[2]
CACHE_PATH = ROOT / "data" / "cache" / "daily_ao_full.json"
AO_URLS = (
    "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/"
    "daily.ao.index.b500.current.ascii",
    "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/"
    "daily.ao.index.b500.current.ascii.gz",
)
AO_MONTHLY_PATH = ROOT / "data" / "global_indices" / "ao_monthly.dat"


def _load_monthly_knots() -> list[tuple[datetime, float]]:
    if not AO_MONTHLY_PATH.exists():
        return []
    knots: list[tuple[datetime, float]] = []
    for line in AO_MONTHLY_PATH.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 3:
            try:
                y, m = int(parts[0]), int(parts[1])
                v = float(parts[2])
                knots.append((datetime(y, m, 15), v))
            except (ValueError, IndexError):
                continue
    knots.sort(key=lambda t: t[0])
    return knots


def _interpolated_daily_from_monthly() -> dict[str, float]:
    knots = _load_monthly_knots()
    if len(knots) < 2:
        return {}
    out: dict[str, float] = {}
    for i in range(len(knots) - 1):
        t0, v0 = knots[i]
        t1, v1 = knots[i + 1]
        span = max((t1 - t0).days, 1)
        d = t0
        while d < t1:
            frac = (d - t0).days / span
            out[d.strftime("%Y-%m-%d")] = float(v0 + frac * (v1 - v0))
            d += timedelta(days=1)
    t_last, v_last = knots[-1]
    nd = calendar.monthrange(t_last.year, t_last.month)[1]
    end_m = datetime(t_last.year, t_last.month, nd)
    d = t_last
    while d <= end_m:
        out[d.strftime("%Y-%m-%d")] = float(v_last)
        d += timedelta(days=1)
    return out


class DailyAOArchive:
    def __init__(self, *, use_network: bool = True) -> None:
        self.use_network = use_network

    def fetch_full_archive(self) -> dict[str, float]:
        """
        Map 'YYYY-MM-DD' -> AO value. Re-fetch if cache missing or older than 7 days
        (when use_network).
        """
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if CACHE_PATH.exists():
            age_days = (datetime.now() - datetime.fromtimestamp(CACHE_PATH.stat().st_mtime)).days
            if age_days < 7 or not self.use_network:
                try:
                    raw = json.loads(CACHE_PATH.read_text())
                    if isinstance(raw, dict):
                        return {
                            str(k): float(v)
                            for k, v in raw.items()
                            if isinstance(k, str) and len(k) == 10 and k[4] == "-"
                        }
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

        if not self.use_network:
            if CACHE_PATH.exists():
                try:
                    raw = json.loads(CACHE_PATH.read_text())
                    if isinstance(raw, dict):
                        return {
                            str(k): float(v)
                            for k, v in raw.items()
                            if isinstance(k, str) and len(k) == 10 and k[4] == "-"
                        }
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
            alt = ROOT / "data" / "cache" / "scouts" / "daily_ao.json"
            if alt.exists():
                try:
                    raw = json.loads(alt.read_text())
                    if isinstance(raw, list):
                        return {str(a[0]): float(a[1]) for a in raw if len(a) >= 2}
                except (json.JSONDecodeError, TypeError, ValueError, IndexError):
                    pass
            return {}

        archive: dict[str, float] = {}
        for url in AO_URLS:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0 (research)"})
                raw = urllib.request.urlopen(req, timeout=45).read()
                if url.endswith(".gz"):
                    import gzip

                    data = gzip.decompress(raw).decode("utf-8", errors="replace")
                else:
                    data = raw.decode("utf-8", errors="replace")
                for line in data.strip().split("\n"):
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                            ao_val = float(parts[3])
                            if abs(ao_val) < 10:
                                archive[f"{year}-{month:02d}-{day:02d}"] = ao_val
                        except (ValueError, IndexError):
                            continue
                if archive:
                    CACHE_PATH.write_text(json.dumps(archive))
                    return archive
            except Exception:
                continue

        era5 = load_era5_daily_ao_archive(ERA5_DAILY_AO_ARCHIVE_PATH)
        if era5:
            CACHE_PATH.write_text(json.dumps(era5))
            return era5

        archive = _interpolated_daily_from_monthly()
        if archive:
            CACHE_PATH.write_text(json.dumps(archive))
        return archive

    def get_pre_outbreak_features(
        self, outbreak_date: datetime, archive: dict[str, float] | None = None
    ) -> dict[str, float | int]:
        """
        Daily AO in the 35 days *before* outbreak_date (not including outbreak day):
        index 0 = D-1, index 13 = D-14, etc.
        """
        if archive is None:
            archive = self.fetch_full_archive()

        ao_vals_35d: list[float] = []
        for days_back in range(1, 36):
            check = outbreak_date - timedelta(days=days_back)
            date_str = check.strftime("%Y-%m-%d")
            if date_str in archive:
                ao_vals_35d.append(archive[date_str])

        if not ao_vals_35d:
            return {
                "ao_min_35d": 0.0,
                "ao_trend_14d": 0.0,
                "ao_trend_7d": 0.0,
                "ao_plunge_14d": 0,
                "ao_plunge_7d": 0,
                "ao_days_negative": 0,
                "ao_consecutive_negative": 0,
            }

        ao_arr = np.array(ao_vals_35d, dtype=np.float64)
        features: dict[str, float | int] = {}
        features["ao_min_35d"] = float(np.min(ao_arr))

        if len(ao_arr) >= 14:
            features["ao_trend_14d"] = float(ao_arr[0] - ao_arr[13])
        else:
            features["ao_trend_14d"] = 0.0

        if len(ao_arr) >= 7:
            features["ao_trend_7d"] = float(ao_arr[0] - ao_arr[6])
        else:
            features["ao_trend_7d"] = 0.0

        plunge_14d = False
        for i in range(len(ao_arr) - 14):
            if float(ao_arr[i] - ao_arr[i + 14]) < -1.5:
                plunge_14d = True
                break
        features["ao_plunge_14d"] = int(plunge_14d)

        plunge_7d = False
        for i in range(len(ao_arr) - 7):
            if float(ao_arr[i] - ao_arr[i + 7]) < -1.0:
                plunge_7d = True
                break
        features["ao_plunge_7d"] = int(plunge_7d)

        features["ao_days_negative"] = int(np.sum(ao_arr < -0.5))

        max_streak = cur_streak = 0
        for v in ao_arr:
            if v < -0.5:
                cur_streak += 1
                max_streak = max(max_streak, cur_streak)
            else:
                cur_streak = 0
        features["ao_consecutive_negative"] = max_streak

        return features
