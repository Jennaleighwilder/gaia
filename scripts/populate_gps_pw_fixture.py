#!/usr/bin/env python3
"""
Populate GPS-PW fixture from UCAR COSMIC Suominet data.

Data: https://data.cosmic.ucar.edu/suominet/postProcess/ncConus/
UNAVCO: https://www.unavco.org/data/tropospheric/pwv/pwv.html

Nearest station to East TN: P778 (Huntsville AL, -85.81, 35.24) — ~150 km from Knoxville.
Uses daily netCDF files. Requires netCDF4: pip install netCDF4

Usage: python scripts/populate_gps_pw_fixture.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts._http_fetch import fetch_bytes
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "gps_pw.json"

# Nearest COSMIC station to East TN (TRI/TYS/GKT)
# P778: Huntsville AL, -85.81, 35.24 — regional proxy for column moisture
EAST_TN_GPS_STATION = "P778"

NC_BASE = "https://data.cosmic.ucar.edu/suominet/postProcess/ncConus"
ASCII_BASE = "https://data.cosmic.ucar.edu/suominet/postProcess/pwvConus"

# Alabama stations (nearest to East TN) — use as regional proxy when P778 not in netCDF
REGIONAL_STATIONS = {"P778", "AL30", "AL50", "AL60", "AL90", "GNVL"}


def doy_from_date(date_str: str) -> tuple[int, int]:
    """Return (year, day_of_year) for YYYY-MM-DD."""
    dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
    return dt.year, int(dt.strftime("%j"))


_NETCDF_WARNED = False


def fetch_and_parse_netcdf(year: int, doy: int) -> dict[str, float] | None:
    """Download daily netCDF, extract PWV by station. Returns {station_id: pWV_mm} or None."""
    global _NETCDF_WARNED
    try:
        import netCDF4
    except ImportError:
        if not _NETCDF_WARNED:
            _NETCDF_WARNED = True
            print("pip install netCDF4 required for GPS-PW netCDF; using ASCII fallback", file=sys.stderr)
        return None

    url = f"{NC_BASE}/y{year}/CsuPWVd_{year}.{doy:03d}.00.00.1440_nc"
    try:
        data = fetch_bytes(url, timeout=30)
    except Exception as e:
        print(f"  fetch failed {url}: {e}", file=sys.stderr)
        return None

    try:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as f:
            f.write(data)
            f.flush()
            ds = netCDF4.Dataset(f.name, "r")
            # CSU Suominet netCDF: PWV (mm), station dimension; try common names
            stations = None
            for name in ("station", "Station", "station_id", "stations"):
                if name in ds.variables:
                    stations = ds.variables[name]
                    break
            pwv = None
            for name in ("PWV", "pwv", "pw", "precipitable_water"):
                if name in ds.variables:
                    pwv = ds.variables[name]
                    break
            if pwv is None:
                for v in list(ds.variables):
                    if "pw" in v.lower() or "precip" in v.lower():
                        pwv = ds.variables[v]
                        break
            if stations is None or pwv is None:
                ds.close()
                Path(f.name).unlink(missing_ok=True)
                return None
            out = {}
            stas = stations[:] if hasattr(stations, "__getitem__") else []
            vals = pwv[:] if hasattr(pwv, "__getitem__") else []
            try:
                import numpy as np
                vals_flat = np.asarray(vals).flatten()
            except Exception:
                vals_flat = list(vals) if hasattr(vals, "__iter__") else []
            for i, sta in enumerate(stas):
                name = sta.decode().strip() if isinstance(sta, bytes) else str(sta).strip()
                if not name:
                    continue
                if i < len(vals_flat):
                    v = vals_flat[i] if hasattr(vals_flat, "__getitem__") else (vals[i] if i < len(vals) else None)
                    if v is not None and isinstance(v, (int, float)) and v == v:
                        out[name] = round(float(v), 2)
            ds.close()
            Path(f.name).unlink(missing_ok=True)
            return out
    except Exception as e:
        print(f"  parse failed: {e}", file=sys.stderr)
        return None


def fetch_openmeteo_batch(dates: list[str]) -> dict[str, float]:
    """
    Fallback: Open-Meteo Historical API (ERA5 reanalysis), single batch request.
    Uses daily dewpoint_2m_mean to approximate column moisture (mm). No API key.
    PW (mm) ≈ 1.2 * (Td + 9). Returns {date_str: pw_mm}.
    """
    if not dates:
        return {}
    start = min(dates)
    end = max(dates)
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude=35.97&longitude=-83.95"
        f"&start_date={start}&end_date={end}"
        "&daily=dewpoint_2m_mean&format=json"
    )
    try:
        data = fetch_bytes(url, timeout=60)
        raw = json.loads(data.decode("utf-8"))
        daily = raw.get("daily", {})
        times = daily.get("time", [])
        dews = daily.get("dewpoint_2m_mean", [])
        date_set = set(dates)
        out = {}
        for t, td in zip(times, dews):
            if t in date_set and td is not None:
                pw = max(5.0, min(60.0, round(1.2 * (float(td) + 9), 2)))
                out[t] = pw
        return out
    except Exception as e:
        print(f"  Open-Meteo fallback failed: {e}", file=sys.stderr)
        return {}


def fetch_and_parse_ascii(year: int, doy: int) -> dict[str, float] | None:
    """
    Fallback: ASCII PWV from pwvConus (no netCDF4 required).
    Format: Site YYYMMDD/HHMM MIN PWV[mm] ... — fixed-width, PWV at col ~30.
    Returns daily mean per station.
    """
    url = f"{ASCII_BASE}/y{year}/SUOd_{year}.{doy:03d}.00.PWV"
    try:
        text = fetch_bytes(url, timeout=60).decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ascii fetch failed {url}: {e}", file=sys.stderr)
        return None
    # Parse: Site (4), YYYMMDD/HHMM, MIN, PWV, ...
    by_station: dict[str, list[float]] = {}
    for line in text.splitlines():
        line = line.rstrip()
        if len(line) < 30 or "Site" in line or "YYYMMDD" in line or not line[0].isalnum():
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        site = parts[0][:4] if len(parts[0]) >= 4 else parts[0]
        try:
            pwv = float(parts[3])
        except (ValueError, IndexError):
            continue
        if pwv < 0 or pwv > 100:
            continue
        by_station.setdefault(site, []).append(pwv)
    if not by_station:
        return None
    # Daily mean per station; prefer regional stations
    out = {}
    for site, vals in by_station.items():
        out[site] = round(sum(vals) / len(vals), 2)
    return out


def get_dates_to_fetch() -> list[str]:
    """Collect event dates + false alarm quiet dates."""
    dates = set()
    events = json.loads((ROOT / "tests" / "fixtures" / "east_tn_severe_events.json").read_text())
    for e in events:
        dates.add(e["date"])
    for p in (ROOT / "tests" / "fixtures" / "historical_observations").glob("quiet_*.json"):
        d = json.loads(p.read_text())
        date_val = d.get("date")
        if not date_val and "_" in p.stem:
            parts = p.stem.split("_")
            if len(parts) >= 2 and "-" in parts[1]:
                date_val = parts[1]
        if date_val:
            dates.add(date_val)
    return sorted(dates)


def _pick_regional_value(parsed: dict[str, float]) -> float | None:
    """Use P778 or other regional station if available, else first value."""
    for sta in REGIONAL_STATIONS:
        if sta in parsed:
            return parsed[sta]
    return next(iter(parsed.values()), None) if parsed else None


def main() -> None:
    dates = get_dates_to_fetch()
    print(f"Fetching GPS-PW for {len(dates)} dates...")
    fixture = {}
    for date_str in dates:
        year, doy = doy_from_date(date_str)
        parsed = fetch_and_parse_netcdf(year, doy)
        if parsed is None:
            parsed = fetch_and_parse_ascii(year, doy)
        val = _pick_regional_value(parsed) if parsed else None
        if val is not None:
            fixture[date_str] = {
                "P778": val, "TYS": val, "TRI": val, "GKT": val,
            }
            print(f"  {date_str}: {val} mm")

    # If UCAR failed for all, try Open-Meteo batch (one request for entire range)
    missing = [d for d in dates if d not in fixture]
    if missing:
        print("  UCAR unavailable; trying Open-Meteo (ERA5) batch...", file=sys.stderr)
        om = fetch_openmeteo_batch(missing)
        for date_str, pw in om.items():
            fixture[date_str] = {"P778": pw, "TYS": pw, "TRI": pw, "GKT": pw}
            print(f"  {date_str}: {pw} mm (Open-Meteo)")
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(fixture, indent=2) + "\n")
    print(f"Wrote {len(fixture)} dates to {FIXTURE_PATH}")


if __name__ == "__main__":
    main()
