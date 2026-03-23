#!/usr/bin/env python3
"""
Populate surface ozone fixture from EPA AQS historical data.

Data: https://aqs.epa.gov/aqsweb/airdata/download_files.html
Daily ozone (44201): daily_44201_{year}.zip

East TN counties (Tennessee FIPS 47):
  Knox 093, Washington 179, Sullivan 163, Greene 059, Hawkins 073,
  Hamblen 063, Grainger 057, Sevier 155, Blount 009

Uses Arithmetic Mean (ppb) as daily value. Nearest East TN monitors.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import zipfile
from io import BytesIO, TextIOWrapper
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts._http_fetch import fetch_bytes

FIXTURE_PATH = ROOT / "tests" / "fixtures" / "surface_ozone.json"

# Tennessee = 47. East TN counties (FIPS, 3-digit; AQS uses "001", "093", etc.)
EAST_TN_STATE = "47"
EAST_TN_COUNTIES = {"001", "009", "057", "059", "063", "073", "093", "155", "163", "179"}

BASE_URL = "https://aqs.epa.gov/aqsweb/airdata"


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


def fetch_year_bulk(year: int) -> dict[str, float]:
    """
    Download daily_44201_{year}.zip, extract CSV, filter East TN.
    Returns { "YYYY-MM-DD": ppb } using Arithmetic Mean.
    """
    url = f"{BASE_URL}/daily_44201_{year}.zip"
    try:
        data = fetch_bytes(url, timeout=90)
    except Exception as e:
        print(f"  bulk fetch failed {url}: {e}", file=sys.stderr)
        return {}

    out: dict[str, list[float]] = {}
    try:
        with zipfile.ZipFile(BytesIO(data), "r") as zf:
            names = zf.namelist()
            csv_name = next((n for n in names if n.endswith(".csv")), None)
            if not csv_name:
                return {}
            with zf.open(csv_name) as f:
                reader = csv.DictReader(TextIOWrapper(f, encoding="utf-8-sig", errors="replace"))
                for row in reader:
                    state = row.get("State Code", "").strip()
                    county = row.get("County Code", "").strip().zfill(3)
                    county = county.zfill(3) if len(county) < 3 else county
                    if state != EAST_TN_STATE or county not in EAST_TN_COUNTIES:
                        continue
                    date_local = row.get("Date Local", "").strip()
                    if not date_local:
                        continue
                    try:
                        mean_str = row.get("Arithmetic Mean", "").strip()
                        if not mean_str:
                            mean_str = row.get("1st Max Value", "").strip()
                        val = float(mean_str)
                    except (ValueError, TypeError):
                        continue
                    # Units: ozone is usually ppb in AQS; if ppm, multiply by 1000
                    units = (row.get("Units of Measure") or "").upper()
                    if "PPM" in units:
                        val = val * 1000.0
                    if date_local not in out:
                        out[date_local] = []
                    out[date_local].append(val)
    except Exception as e:
        print(f"  parse failed for {year}: {e}", file=sys.stderr)
        return {}

    # Average across monitors per date
    return {d: round(sum(vals) / len(vals), 1) for d, vals in out.items() if vals}


def fetch_year_api(year: int, email: str, key: str) -> dict[str, float]:
    """
    Fallback: EPA AQS API dailyData/byState (param 44201).
    Requires AQS_API_EMAIL and AQS_API_KEY env vars. Sign up: aqs.epa.gov/data/api/signup
    """
    import urllib.parse

    bdate = f"{year}0101"
    edate = f"{year}1231"
    url = (
        "https://aqs.epa.gov/data/api/dailyData/byState"
        f"?email={urllib.parse.quote(email)}&key={urllib.parse.quote(key)}"
        f"&param=44201&bdate={bdate}&edate={edate}&state=47"
    )
    try:
        data = fetch_bytes(url, timeout=60)
        raw = json.loads(data.decode("utf-8"))
    except Exception as e:
        print(f"  AQS API failed for {year}: {e}", file=sys.stderr)
        return {}
    if raw.get("Header", {}).get("status") != "Success":
        print(f"  AQS API error for {year}: {raw.get('Data', raw)}", file=sys.stderr)
        return {}
    # Filter East TN counties
    out: dict[str, list[float]] = {}
    for r in raw.get("Data", []):
        county = (r.get("county_code") or "").strip().zfill(3)
        if county not in EAST_TN_COUNTIES:
            continue
        date_local = (r.get("date_local") or "").strip()
        if not date_local:
            continue
        try:
            val = float(r.get("arithmetic_mean") or r.get("first_max_value") or 0)
        except (ValueError, TypeError):
            continue
        units = (r.get("units_of_measure") or "").upper()
        if "PPM" in units:
            val = val * 1000.0
        out.setdefault(date_local, []).append(val)
    return {d: round(sum(v) / len(v), 1) for d, v in out.items() if v}


def fetch_year(year: int) -> dict[str, float]:
    """Bulk first; if 403/empty, try AQS API when AQS_API_EMAIL/KEY set."""
    out = fetch_year_bulk(year)
    if out:
        return out
    email = os.environ.get("AQS_API_EMAIL", "").strip()
    key = os.environ.get("AQS_API_KEY", "").strip()
    if email and key:
        print(f"  Trying AQS API for {year}...", file=sys.stderr)
        return fetch_year_api(year, email, key)
    return {}


def main() -> None:
    dates = get_dates_to_fetch()
    years = sorted({d[:4] for d in dates})
    print(f"Fetching surface ozone for {len(dates)} dates across years {years}...")

    by_year = {}
    for year in years:
        yr = int(year)
        by_year[year] = fetch_year(yr)
        print(f"  {year}: {len(by_year[year])} dates with data")

    fixture = {}
    missing = []
    for d in dates:
        yr = d[:4]
        if d in by_year.get(yr, {}):
            fixture[d] = by_year[yr][d]
        else:
            missing.append(d)

    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(fixture, indent=2) + "\n")
    print(f"Wrote {len(fixture)} dates to {FIXTURE_PATH}")
    if missing:
        print(f"Missing ({len(missing)}): {missing[:10]}{'...' if len(missing) > 10 else ''}")
        if not os.environ.get("AQS_API_EMAIL") or not os.environ.get("AQS_API_KEY"):
            print(
                "  For ozone: set AQS_API_EMAIL and AQS_API_KEY (free signup at aqs.epa.gov/data/api/signup)",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
