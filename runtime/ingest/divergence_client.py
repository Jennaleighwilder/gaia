"""
200mb horizontal divergence (Mississippi Valley box) from NCEP/NCAR monthly u,v.
div ≈ (1/(a cos φ)) ∂u/∂λ + (1/a) ∂v/∂φ (λ, φ in radians).
One open of uwnd/vwnd per monthly fetch; one open pair for full 1981–2010 climo build.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache" / "div200"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

UWND_URL = (
    "https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis.derived/pressure/uwnd.mon.mean.nc"
)
VWND_URL = (
    "https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis.derived/pressure/vwnd.mon.mean.nc"
)

EARTH_RADIUS_M = 6_371_000.0


def _xr_engine() -> str:
    try:
        import netCDF4  # noqa: F401

        return "netcdf4"
    except ImportError:
        return "pydap"


def _mean_div_from_open(u_ds, v_ds, year: int, month: int) -> float:
    t = f"{year}-{month:02d}-01"
    u = u_ds["uwnd"].sel(time=t, method="nearest", level=200).sel(
        lat=slice(40, 30), lon=slice(265, 280)
    )
    v = v_ds["vwnd"].sel(time=t, method="nearest", level=200).sel(
        lat=slice(40, 30), lon=slice(265, 280)
    )
    U = np.asarray(u.values, dtype=np.float64)
    V = np.asarray(v.values, dtype=np.float64)
    lat_rad = np.deg2rad(np.asarray(u["lat"].values, dtype=np.float64))
    lon_rad = np.deg2rad(np.asarray(u["lon"].values, dtype=np.float64))
    a = EARTH_RADIUS_M
    nlat, nlon = U.shape
    du_dlam = np.zeros_like(U)
    for i in range(nlat):
        cos_phi = max(np.cos(lat_rad[i]), 0.2)
        du_dlam[i, :] = np.gradient(U[i, :], lon_rad) / (a * cos_phi)
    dv_dphi = np.gradient(V, lat_rad, axis=0) / a
    div = du_dlam + dv_dphi
    return float(np.mean(div))


class DivergenceClient:
    def __init__(self, *, use_network: bool = True) -> None:
        self.use_network = use_network

    def _climo_div(self, month: int) -> float:
        idx = CACHE_DIR / "div200_climo_1981_2010.json"
        data: dict = {}
        if idx.exists():
            try:
                data = json.loads(idx.read_text())
            except json.JSONDecodeError:
                data = {}
        key = f"m{month:02d}"
        if key in data:
            return float(data[key])

        if not self.use_network:
            return 0.0

        import xarray as xr

        eng = _xr_engine()
        u_ds = xr.open_dataset(UWND_URL, engine=eng)
        v_ds = xr.open_dataset(VWND_URL, engine=eng)
        try:
            vals = [_mean_div_from_open(u_ds, v_ds, y, month) for y in range(1981, 2011)]
            m = sum(vals) / len(vals)
            data[key] = m
            idx.write_text(json.dumps(data, indent=0) + "\n")
            return m
        finally:
            u_ds.close()
            v_ds.close()

    def get_upper_divergence(self, year: int, month: int) -> dict:
        cache = CACHE_DIR / f"div200_{year}_{month:02d}.json"
        if cache.exists():
            try:
                return json.loads(cache.read_text())
            except json.JSONDecodeError:
                pass

        if not self.use_network:
            return {
                "div_200mb": 0.0,
                "div_200mb_anomaly": 0.0,
                "jet_exit_over_corridor": False,
                "source": "offline_no_cache",
            }

        try:
            import xarray as xr

            eng = _xr_engine()
            u_ds = xr.open_dataset(UWND_URL, engine=eng)
            v_ds = xr.open_dataset(VWND_URL, engine=eng)
            try:
                div = _mean_div_from_open(u_ds, v_ds, year, month)
            finally:
                u_ds.close()
                v_ds.close()
            climo = self._climo_div(month)
            anom = div - climo
            result = {
                "div_200mb": round(div, 8),
                "div_200mb_anomaly": round(anom, 8),
                "jet_exit_over_corridor": bool(anom > 0.0),
                "source": "ncep_reanalysis_uv",
            }
            cache.write_text(json.dumps(result))
            return result
        except Exception as e:
            return {
                "div_200mb": 0.0,
                "div_200mb_anomaly": 0.0,
                "jet_exit_over_corridor": False,
                "source": f"unavailable:{e!s}"[:80],
            }
