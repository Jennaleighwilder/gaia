"""
Daily Arctic Oscillation index from ERA5 (Copernicus CDS), independent of NOAA CPC.

Uses 1000 hPa geopotential over 20–90°N, EOF1 loading on monthly anomalies (1979–2000),
then projects daily anomalies (vs 1981–2010 monthly climatology) onto that loading.

Requires (CDS): pip install cdsapi; ~/.cdsapirc (see scripts/cds_connection_test.py).

Local NetCDF from CDS: use `import_netcdf_daily_to_cache` / `import_netcdf_monthly_to_cache`
(netCDF4 + xarray). Handles `valid_time`, 0–360° longitude, and 1000 hPa `z` → height (m).
"""

from __future__ import annotations

import calendar
import json
import tempfile
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache" / "era5_daily_ao"
AO_LOADING_PATTERN_FILE = CACHE_DIR / "ao_loading_pattern.npy"
# Merge period outputs into this path for DailyAOArchive to consume when CPC is down.
ERA5_DAILY_AO_ARCHIVE_PATH = CACHE_DIR / "daily_ao_archive.json"

G = 9.80665

DATASET_MONTHLY = "reanalysis-era5-pressure-levels-monthly-means"
DATASET_DAILY = "derived-era5-pressure-levels-daily-statistics"

# NH subdomain (N, W, S, E) — matches CPC-style AO domain (poleward of ~20°N).
AO_AREA = [90, -180, 20, 180]


def _first_eof_loading(X_centered: np.ndarray) -> tuple[np.ndarray, float]:
    """EOF1 via SVD; X_centered shape (n_time, n_space). Returns (loading, explained_var_ratio)."""
    _u, s, vt = np.linalg.svd(X_centered, full_matrices=False)
    loading = vt[0].astype(np.float64, copy=False)
    ev = float((s[0] ** 2) / np.sum(s**2)) if s.size else 0.0
    return loading, ev


def _z_to_height_m(values: np.ndarray) -> np.ndarray:
    return values / G


def _find_geopotential_name(ds) -> str:
    for name in ("z", "Z", "geopotential"):
        if name in ds.variables or name in ds.data_vars:
            return name
    raise KeyError("no geopotential variable (expected z or geopotential)")


def _open_cds_download(path: Path):
    """Open NetCDF from CDS target path (plain .nc or .zip containing .nc). Loads into memory."""
    import xarray as xr

    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf, tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            nc_members = [n for n in zf.namelist() if n.lower().endswith(".nc")]
            if not nc_members:
                raise ValueError(f"ZIP has no .nc member: {path}")
            zf.extract(nc_members[0], td_path)
            with xr.open_dataset(td_path / nc_members[0]) as ds:
                return ds.load()
    with xr.open_dataset(path) as ds:
        return ds.load()


def _retrieve_to_dataset(client, dataset: str, request: dict):
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        target = tdir / "cds_out"
        client.retrieve(dataset, request, str(target))
        paths = sorted(tdir.iterdir())
        if not paths:
            raise FileNotFoundError("CDS retrieve wrote no files")
        return _open_cds_download(paths[0])


def _normalize_longitude_dataset(ds):
    """Map longitude to [-180, 180] and sort (CDS GRIB→NetCDF often uses 0..360)."""
    if "longitude" not in ds.coords and "lon" in ds.coords:
        ds = ds.rename({"lon": "longitude"})
    if "longitude" not in ds.coords:
        return ds
    if float(ds.longitude.max()) <= 180.0:
        return ds
    new_lon = ((ds.longitude + 180) % 360) - 180
    return ds.assign_coords(longitude=new_lon).sortby("longitude")


def _time_dim_name(ds) -> str:
    if "valid_time" in ds.dims:
        return "valid_time"
    if "time" in ds.dims:
        return "time"
    raise ValueError("dataset has neither valid_time nor time dimension")


def _daily_heights_dict_from_dataset(ds) -> dict[str, list[float]]:
    """1000 hPa NH (20–90°N) height (m), one flattened field per time."""
    import pandas as pd

    ds = _normalize_longitude_dataset(ds)
    name = _find_geopotential_name(ds)
    z = ds[name].astype("float64")
    z = z / G
    td = _time_dim_name(z)
    if "pressure_level" in z.dims:
        if z.sizes["pressure_level"] > 1:
            z = z.sel(pressure_level=1000.0, method="nearest")
        z = z.squeeze("pressure_level", drop=True)
    if "lat" in z.dims:
        z = z.rename({"lat": "latitude"})
    nh = z.sel(latitude=slice(90, 20))
    out: dict[str, list[float]] = {}
    for i in range(int(nh.sizes[td])):
        tv = nh[td].values[i]
        date_str = pd.Timestamp(tv).strftime("%Y-%m-%d")
        out[date_str] = nh.isel({td: i}).values.astype(np.float64).ravel().tolist()
    return out


def import_netcdf_daily_to_cache(nc_path: Path | str, year: int, month: int) -> dict[str, list[float]]:
    """
    Read a CDS daily NetCDF (e.g. derived daily statistics) and write
    `hgt1000_daily_{year}_{month:02d}.json` — same format as API path (no retrieve).
    """
    import xarray as xr

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(nc_path)
    cache = CACHE_DIR / f"hgt1000_daily_{year}_{month:02d}.json"
    with xr.open_dataset(path) as ds:
        ds = _normalize_longitude_dataset(ds.load())
        hgts = _daily_heights_dict_from_dataset(ds)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(hgts, f)
    return hgts


def import_netcdf_monthly_to_cache(nc_path: Path | str, year: int, month: int) -> np.ndarray:
    """
    Read a CDS monthly-mean NetCDF and write `hgt1000_monthly_{year}_{month:02d}.npy` (no retrieve).
    """
    import xarray as xr

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(nc_path)
    cache = CACHE_DIR / f"hgt1000_monthly_{year}_{month:02d}.npy"
    with xr.open_dataset(path) as ds:
        ds = _normalize_longitude_dataset(ds.load())
        name = _find_geopotential_name(ds)
        z = ds[name].astype("float64") / G
        td = None
        if "valid_time" in z.dims:
            td = "valid_time"
        elif "time" in z.dims:
            td = "time"
        if td is not None:
            z = z.isel({td: 0}, drop=True)
        if "pressure_level" in z.dims:
            if z.sizes.get("pressure_level", 1) > 1:
                z = z.sel(pressure_level=1000.0, method="nearest")
            z = z.squeeze("pressure_level", drop=True)
        if "lat" in z.dims:
            z = z.rename({"lat": "latitude"})
        nh = z.sel(latitude=slice(90, 20))
        hgt = np.asarray(nh.values, dtype=np.float64)
    np.save(cache, hgt)
    return hgt


def compute_intramonth_eof_daily_ao(hgts: dict[str, list[float]]) -> dict[str, float]:
    """
    When full 1979–2000 EOF + 1981–2010 climatology are unavailable, build a **month-local**
    index: EOF1 of NH height anomalies (each day minus its grid-point mean over the month),
    then **standardize** PC1 scores to ~mean 0 / std 1 within that month (comparable across
    months). This is **not** the official CPC AO; use it to see sub-monthly swings (e.g. dips)
    in the leading NH pattern.
    """
    dates = sorted(hgts.keys())
    if len(dates) < 3:
        raise ValueError("need at least 3 days for intramonth EOF")
    X = np.stack([np.asarray(hgts[d], dtype=np.float64) for d in dates], axis=0)
    X = X - np.mean(X, axis=0, keepdims=True)
    loading, _ev = _first_eof_loading(X)
    loading = loading / (np.linalg.norm(loading) + 1e-30)
    raw = np.array([float(np.dot(X[i], loading)) for i in range(len(dates))])
    sd = float(raw.std())
    if sd < 1e-12:
        sd = 1.0
    z = (raw - raw.mean()) / sd
    return {d: round(float(z[i]), 3) for i, d in enumerate(dates)}


def merge_daily_ao_into_archive(
    new_values: dict[str, float], path: Path | None = None
) -> dict[str, float]:
    """Merge new YYYY-MM-DD AO values into daily_ao_archive.json."""
    p = path or ERA5_DAILY_AO_ARCHIVE_PATH
    cur = load_era5_daily_ao_archive(p)
    cur.update(new_values)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cur, indent=2), encoding="utf-8")
    return cur


class ERA5DailyAO:
    CACHE_DIR = CACHE_DIR
    AO_LOADING_PATTERN_FILE = AO_LOADING_PATTERN_FILE

    def __init__(self) -> None:
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._client = None

    def _get_client(self):
        if self._client is None:
            import cdsapi

            self._client = cdsapi.Client()
        return self._client

    def fetch_monthly_1000mb_heights(self, year: int, month: int) -> np.ndarray:
        """Monthly mean 1000 hPa height (m), shape (n_lat, n_lon). Cached as .npy."""
        cache = self.CACHE_DIR / f"hgt1000_monthly_{year}_{month:02d}.npy"
        if cache.exists():
            return np.load(cache)

        c = self._get_client()
        request = {
            "product_type": ["monthly_averaged_reanalysis"],
            "variable": ["geopotential"],
            "pressure_level": ["1000"],
            "year": [str(year)],
            "month": [f"{month:02d}"],
            "time": ["00:00"],
            "data_format": "netcdf",
            "download_format": "unarchived",
            "area": AO_AREA,
        }
        ds = _retrieve_to_dataset(c, DATASET_MONTHLY, request)
        name = _find_geopotential_name(ds)
        z = ds[name].squeeze()
        hgt = np.asarray(_z_to_height_m(z.values), dtype=np.float64)
        np.save(cache, hgt)
        return hgt

    def compute_ao_loading_pattern(self, base_years: range | None = None) -> np.ndarray:
        """EOF1 of monthly 1000 hPa height anomalies (flattened), 1979–2000 by default."""
        if base_years is None:
            base_years = range(1979, 2001)
        if self.AO_LOADING_PATTERN_FILE.exists():
            return np.load(self.AO_LOADING_PATTERN_FILE)

        print("Computing AO loading pattern from ERA5 (1979-2000)...")
        all_monthly: list[np.ndarray] = []
        for year in base_years:
            for month in range(1, 13):
                try:
                    hgt = self.fetch_monthly_1000mb_heights(year, month)
                    all_monthly.append(hgt.astype(np.float64, copy=False).reshape(-1))
                    print(f"  {year}-{month:02d}")
                except Exception as e:
                    print(f"  Failed {year}-{month:02d}: {e}")

        if not all_monthly:
            raise ValueError("Could not fetch ERA5 monthly data to compute AO pattern")

        X = np.stack(all_monthly, axis=0)
        X_centered = X - X.mean(axis=0)
        loading, ev = _first_eof_loading(X_centered)
        np.save(self.AO_LOADING_PATTERN_FILE, loading)
        print(f"AO loading pattern saved. Approx. EOF1 variance fraction: {ev:.1%}")
        return loading

    def fetch_daily_1000mb_heights(self, year: int, month: int) -> dict[str, list[float]]:
        """Daily mean 1000 hPa height (m); keys 'YYYY-MM-DD', values flattened grid (lists for JSON)."""
        cache = self.CACHE_DIR / f"hgt1000_daily_{year}_{month:02d}.json"
        if cache.exists():
            with open(cache, encoding="utf-8") as f:
                return json.load(f)

        c = self._get_client()
        nd = calendar.monthrange(year, month)[1]
        day_list = [f"{d:02d}" for d in range(1, nd + 1)]
        # Shape matches CDS "Show API request" for derived daily stats (cdsapi 0.7.x).
        request = {
            "product_type": "reanalysis",
            "variable": ["geopotential"],
            "year": str(year),
            "month": [f"{month:02d}"],
            "day": day_list,
            "pressure_level": ["1000"],
            "daily_statistic": "daily_mean",
            "time_zone": "utc+00:00",
            "frequency": "1_hourly",
            "area": AO_AREA,
        }
        ds = _retrieve_to_dataset(c, DATASET_DAILY, request)
        # CDS NetCDF often uses valid_time; reuse same path as local import.
        hgt_data = _daily_heights_dict_from_dataset(ds)
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(hgt_data, f)
        return hgt_data

    def compute_daily_ao_for_period(self, start_year: int, end_year: int) -> dict[str, float]:
        """Daily AO proxy: project daily height anomaly onto EOF1; scaled ~CPC-like via /100."""
        output_cache = self.CACHE_DIR / f"daily_ao_{start_year}_{end_year}.json"
        if output_cache.exists():
            with open(output_cache, encoding="utf-8") as f:
                raw = json.load(f)
            return {str(k): float(v) for k, v in raw.items()}

        loading = self.compute_ao_loading_pattern()
        denom = float(np.dot(loading, loading))
        if denom <= 0:
            raise ValueError("degenerate AO loading")

        print("Computing monthly climatology (1981-2010)...")
        climo: dict[int, np.ndarray] = {}
        for month in range(1, 13):
            monthly_hgts: list[np.ndarray] = []
            for year in range(1981, 2011):
                try:
                    hgt = self.fetch_monthly_1000mb_heights(year, month)
                    monthly_hgts.append(hgt.astype(np.float64, copy=False).reshape(-1))
                except Exception:
                    continue
            if monthly_hgts:
                climo[month] = np.mean(np.stack(monthly_hgts, axis=0), axis=0)

        daily_ao: dict[str, float] = {}
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                print(f"Computing daily AO: {year}-{month:02d}")
                try:
                    daily_hgts = self.fetch_daily_1000mb_heights(year, month)
                    climo_hgt = climo.get(month)
                    if climo_hgt is None:
                        climo_hgt = np.zeros_like(loading)
                    for date_str, hgt_list in daily_hgts.items():
                        hgt_arr = np.asarray(hgt_list, dtype=np.float64)
                        anomaly = hgt_arr - climo_hgt
                        ao_val = float(np.dot(anomaly, loading) / denom)
                        daily_ao[date_str] = round(ao_val / 100.0, 3)
                except Exception as e:
                    print(f"  Failed {year}-{month:02d}: {e}")

        with open(output_cache, "w", encoding="utf-8") as f:
            json.dump(daily_ao, f)
        print(f"Saved {len(daily_ao)} daily AO values -> {output_cache}")
        return daily_ao


def load_era5_daily_ao_archive(path: Path | None = None) -> dict[str, float]:
    """Load merged ERA5 daily AO JSON (YYYY-MM-DD -> float)."""
    p = path or ERA5_DAILY_AO_ARCHIVE_PATH
    if not p.exists():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
        return {str(k): float(v) for k, v in raw.items() if isinstance(k, str) and len(k) == 10 and k[4] == "-"}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}
