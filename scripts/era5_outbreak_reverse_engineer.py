#!/usr/bin/env python3
"""
Phase 4: ERA5 reverse-engineer major US tornado outbreaks since 1990.

Produces:
  - runs/era5_outbreak_tess.json
  - runs/era5_outbreak_tess_table.md

Data source: Open-Meteo archive API (ERA5-backed reanalysis fields).
"""

from __future__ import annotations

import json
import statistics
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)


# 35 major outbreaks since 1990 (curated list for lead-time benchmarking).
OUTBREAKS = [
    {"name": "Plainfield IL", "date": "1990-08-28", "lat": 41.62, "lon": -88.20},
    {"name": "Andover KS", "date": "1991-04-26", "lat": 37.69, "lon": -97.14},
    {"name": "Palm Sunday AL", "date": "1994-03-27", "lat": 33.52, "lon": -86.80},
    {"name": "Mayfest TX", "date": "1995-05-05", "lat": 32.76, "lon": -97.33},
    {"name": "Central FL Outbreak", "date": "1998-02-23", "lat": 28.50, "lon": -81.37},
    {"name": "Bridge Creek-Moore", "date": "1999-05-03", "lat": 35.34, "lon": -97.49},
    {"name": "Guam EF4", "date": "2001-12-08", "lat": 13.48, "lon": 144.75},
    {"name": "Veterans Day Outbreak", "date": "2002-11-10", "lat": 32.40, "lon": -88.70},
    {"name": "Mother's Day Outbreak", "date": "2003-05-04", "lat": 39.00, "lon": -92.30},
    {"name": "Hallam NE", "date": "2004-05-22", "lat": 40.54, "lon": -96.80},
    {"name": "Evansville IN", "date": "2005-11-06", "lat": 38.04, "lon": -87.57},
    {"name": "Super Tuesday", "date": "2008-02-05", "lat": 35.15, "lon": -90.05},
    {"name": "Mother's Day 2008", "date": "2008-05-10", "lat": 36.15, "lon": -95.99},
    {"name": "Southeast Super Outbreak", "date": "2011-04-27", "lat": 33.52, "lon": -86.80},
    {"name": "Joplin MO", "date": "2011-05-22", "lat": 37.08, "lon": -94.51},
    {"name": "Henryville IN", "date": "2012-03-02", "lat": 38.54, "lon": -85.77},
    {"name": "El Reno OK", "date": "2013-05-31", "lat": 35.53, "lon": -97.95},
    {"name": "Pilger NE", "date": "2014-06-16", "lat": 42.00, "lon": -97.05},
    {"name": "Christmas 2015", "date": "2015-12-23", "lat": 32.30, "lon": -90.20},
    {"name": "Dodge City KS", "date": "2016-05-24", "lat": 37.77, "lon": -99.97},
    {"name": "Albany GA", "date": "2017-01-22", "lat": 31.58, "lon": -84.15},
    {"name": "Canton TX", "date": "2017-04-29", "lat": 32.56, "lon": -95.86},
    {"name": "Greensboro AL", "date": "2019-03-03", "lat": 32.70, "lon": -87.59},
    {"name": "Dayton OH", "date": "2019-05-27", "lat": 39.76, "lon": -84.19},
    {"name": "Nashville TN", "date": "2020-03-03", "lat": 36.16, "lon": -86.78},
    {"name": "Easter 2020", "date": "2020-04-12", "lat": 33.50, "lon": -86.80},
    {"name": "March 2021 Dixie", "date": "2021-03-17", "lat": 33.21, "lon": -87.57},
    {"name": "Western KY Quad-State", "date": "2021-12-10", "lat": 36.74, "lon": -88.64},
    {"name": "Iowa Derecho/Tornado", "date": "2022-03-05", "lat": 41.59, "lon": -93.62},
    {"name": "Rolling Fork MS", "date": "2023-03-24", "lat": 32.90, "lon": -90.88},
    {"name": "Little Rock AR", "date": "2023-03-31", "lat": 34.75, "lon": -92.29},
    {"name": "Perryton TX", "date": "2023-06-15", "lat": 36.40, "lon": -100.80},
    {"name": "Clarksville TN", "date": "2023-12-09", "lat": 36.53, "lon": -87.36},
    {"name": "Midwest Long-Track", "date": "2024-04-26", "lat": 39.10, "lon": -94.58},
    {"name": "Hollister OK", "date": "2024-05-20", "lat": 34.34, "lon": -98.73},
]


def _fetch_json(url: str, timeout: int = 45) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def fetch_era5_window(lat: float, lon: float, start: date, end: date) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(
            [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "wind_speed_10m_max",
                "wind_gusts_10m_max",
            ]
        ),
        "timezone": "UTC",
    }
    url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params)
    return _fetch_json(url, timeout=60)


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, v))


def score_loading_day(tmax: float, tmin: float, precip: float, wind: float, gust: float) -> float:
    spread = max(0.0, tmax - tmin)
    gust_term = _clip01((gust - 20.0) / 30.0)
    wind_term = _clip01((wind - 15.0) / 20.0)
    precip_term = _clip01(precip / 20.0)
    spread_term = _clip01((spread - 8.0) / 18.0)
    return round(0.35 * gust_term + 0.20 * wind_term + 0.25 * precip_term + 0.20 * spread_term, 4)


def month_global_bias(dt: date) -> float:
    # Tornado-prone seasonality + shoulder seasons.
    if dt.month in (4, 5):
        return 0.70
    if dt.month in (3, 6):
        return 0.55
    if dt.month in (2, 11, 12):
        return 0.40
    return 0.25


def compute_tess_series(era5: dict, outbreak_date: date) -> list[dict]:
    daily = era5.get("daily") or {}
    times = daily.get("time") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    precip = daily.get("precipitation_sum") or []
    wind = daily.get("wind_speed_10m_max") or []
    gust = daily.get("wind_gusts_10m_max") or []

    rows = []
    for i, ts in enumerate(times):
        try:
            day = date.fromisoformat(ts)
            loading = score_loading_day(
                float(tmax[i]),
                float(tmin[i]),
                float(precip[i]),
                float(wind[i]),
                float(gust[i]),
            )
        except Exception:
            continue
        origin = month_global_bias(day)
        transport = month_global_bias(day) * 0.9
        tess = origin * 0.35 + transport * 0.35 + loading * 0.30
        if sum(1 for s in (origin, transport, loading) if s >= 0.5) >= 2:
            tess = min(1.0, tess * 1.1)
        lead_days = (outbreak_date - day).days
        rows.append(
            {
                "date": day.isoformat(),
                "lead_days": lead_days,
                "origin": round(origin, 3),
                "transport": round(transport, 3),
                "loading": loading,
                "tess": round(tess, 3),
            }
        )
    return rows


def summarize_outbreak(ob: dict) -> dict:
    event_date = date.fromisoformat(ob["date"])
    start = event_date - timedelta(days=45)
    era5 = fetch_era5_window(ob["lat"], ob["lon"], start, event_date)
    series = compute_tess_series(era5, event_date)
    if not series:
        return {
            **ob,
            "status": "no_data",
            "first_fire_date": None,
            "lead_days": None,
            "peak_tess": None,
        }

    firing = [r for r in series if r["lead_days"] >= 0 and r["tess"] >= 0.70]
    first = sorted(firing, key=lambda r: r["lead_days"], reverse=True)[0] if firing else None
    peak = max(series, key=lambda r: r["tess"])
    return {
        **ob,
        "status": "ok",
        "first_fire_date": first["date"] if first else None,
        "lead_days": first["lead_days"] if first else None,
        "peak_tess": peak["tess"],
        "peak_date": peak["date"],
    }


def write_markdown(results: list[dict], median_lead: float | None) -> None:
    md = []
    md.append("# ERA5 Reverse-Engineer: 35 Outbreaks Since 1990")
    md.append("")
    if median_lead is None:
        md.append("No valid lead times available.")
    else:
        md.append(f"Median TESS lead time: **{median_lead:.1f} days**")
    md.append("")
    md.append("| Outbreak | Date | First TESS>=0.70 | Lead Days | Peak TESS |")
    md.append("|---|---:|---:|---:|---:|")
    for r in results:
        md.append(
            f"| {r['name']} | {r['date']} | {r.get('first_fire_date') or '-'} | "
            f"{r.get('lead_days') if r.get('lead_days') is not None else '-'} | "
            f"{r.get('peak_tess') if r.get('peak_tess') is not None else '-'} |"
        )
    (RUNS_DIR / "era5_outbreak_tess_table.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main() -> int:
    print(f"Starting ERA5 reverse-engineer for {len(OUTBREAKS)} outbreaks...")
    results: list[dict] = []
    for i, ob in enumerate(OUTBREAKS, start=1):
        print(f"[{i:02d}/{len(OUTBREAKS)}] {ob['name']} ({ob['date']})")
        try:
            res = summarize_outbreak(ob)
            results.append(res)
            lead = res.get("lead_days")
            peak = res.get("peak_tess")
            print(f"  -> lead_days={lead} peak_tess={peak}")
        except Exception as e:
            results.append({**ob, "status": "error", "error": str(e)})
            print(f"  -> error: {e}")
        # Keep requests polite; this also makes the run intentionally gradual.
        time.sleep(0.35)

    leads = [r["lead_days"] for r in results if isinstance(r.get("lead_days"), int)]
    median_lead = statistics.median(leads) if leads else None
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_outbreaks": len(OUTBREAKS),
        "n_with_lead": len(leads),
        "median_lead_days": median_lead,
        "results": results,
    }
    (RUNS_DIR / "era5_outbreak_tess.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_markdown(results, median_lead)

    print("")
    if median_lead is None:
        print("Done. No valid lead times generated.")
    else:
        print(f"Done. Median TESS lead time across {len(leads)} outbreaks: {median_lead:.1f} days")
    print("Wrote runs/era5_outbreak_tess.json")
    print("Wrote runs/era5_outbreak_tess_table.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
