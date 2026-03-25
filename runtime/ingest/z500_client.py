"""
NCEP/NCAR Reanalysis 1 — monthly mean 500mb height anomalies (PSL OPeNDAP).
Single dataset open per climatology build / per monthly fetch.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache" / "z500"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HGT_URL = (
    "https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis.derived/pressure/hgt.mon.mean.nc"
)


def _xr_engine() -> str:
    try:
        import netCDF4  # noqa: F401

        return "netcdf4"
    except ImportError:
        return "pydap"


def _box_mean_from_ds(ds, year: int, month: int, lat0: float, lat1: float, lon0: float, lon1: float) -> float:
    t = f"{year}-{month:02d}-01"
    h = ds["hgt"].sel(level=500, time=t, method="nearest")
    return float(h.sel(lat=slice(lat0, lat1), lon=slice(lon0, lon1)).mean().values)


class Z500Client:
    def __init__(self, *, use_network: bool = True) -> None:
        self.use_network = use_network

    def _climo_pair(self, month: int) -> tuple[float, float]:
        idx = CACHE_DIR / "z500_climo_1981_2010.json"
        data: dict = {}
        if idx.exists():
            try:
                data = json.loads(idx.read_text())
            except json.JSONDecodeError:
                data = {}
        key = f"m{month:02d}"
        if key in data:
            return float(data[key]["central"]), float(data[key]["ridge"])

        if not self.use_network:
            return 0.0, 0.0

        import xarray as xr

        eng = _xr_engine()
        ds = xr.open_dataset(HGT_URL, engine=eng)
        try:
            centrals: list[float] = []
            ridges: list[float] = []
            for y in range(1981, 2011):
                centrals.append(_box_mean_from_ds(ds, y, month, 50, 30, 260, 280))
                ridges.append(_box_mean_from_ds(ds, y, month, 45, 35, 250, 270))
            c = sum(centrals) / len(centrals)
            r = sum(ridges) / len(ridges)
            data[key] = {"central": c, "ridge": r}
            idx.write_text(json.dumps(data, indent=0) + "\n")
            return c, r
        finally:
            ds.close()

    def get_z500_anomaly(self, year: int, month: int) -> dict:
        cache = CACHE_DIR / f"z500_{year}_{month:02d}.json"
        if cache.exists():
            try:
                return json.loads(cache.read_text())
            except json.JSONDecodeError:
                pass

        if not self.use_network:
            return {
                "z500_anomaly_central_us": 0.0,
                "z500_ridge_anomaly_rockies": 0.0,
                "trough_over_central_us": False,
                "ridge_over_rockies": False,
                "jet_amplification": 0.0,
                "source": "offline_no_cache",
            }

        last_err: Exception | None = None
        for attempt in range(3):
            try:
                import xarray as xr

                eng = _xr_engine()
                ds = xr.open_dataset(HGT_URL, engine=eng)
                try:
                    h_c = _box_mean_from_ds(ds, year, month, 50, 30, 260, 280)
                    h_r = _box_mean_from_ds(ds, year, month, 45, 35, 250, 270)
                finally:
                    ds.close()
                climo_c, climo_r = self._climo_pair(month)
                anomaly = h_c - climo_c
                ridge_anom = h_r - climo_r
                jet_amp = abs(anomaly - ridge_anom) / 30.0
                result = {
                    "z500_anomaly_central_us": round(float(anomaly), 1),
                    "z500_ridge_anomaly_rockies": round(float(ridge_anom), 1),
                    "trough_over_central_us": bool(anomaly < -20),
                    "ridge_over_rockies": bool(ridge_anom > 20),
                    "jet_amplification": round(float(jet_amp), 2),
                    "source": "ncep_reanalysis",
                }
                cache.write_text(json.dumps(result))
                return result
            except Exception as e:
                last_err = e
                if "429" in str(e) and attempt < 2:
                    time.sleep(8.0 * (attempt + 1))
                    continue
                break
        return {
            "z500_anomaly_central_us": 0.0,
            "z500_ridge_anomaly_rockies": 0.0,
            "trough_over_central_us": False,
            "ridge_over_rockies": False,
            "jet_amplification": 0.0,
            "source": f"unavailable:{last_err!s}"[:80],
        }
