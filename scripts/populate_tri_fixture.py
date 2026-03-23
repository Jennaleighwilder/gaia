#!/usr/bin/env python3
"""
Populate TRI (Toxics Release Inventory) facility fixture for East TN.

Sources:
- EPA TRI Basic Data Files: https://www.epa.gov/toxics-release-inventory-tri-program/tri-basic-data-files-calendar-years-1987-present
- Manual: Download TRI state file for TN, save as tests/fixtures/tri_tn_raw.csv
- EPA ECHO/FRS APIs (alternative)

Monitored East TN counties (FIPS 47-XXX):
  Knox 093, Sevier 155, Blount 009, Greene 059, Hamblen 063,
  Hawkins 073, Washington 179, Grainger 057, Sullivan 163

Output: tests/fixtures/tri_facilities_tn.json
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "tri_facilities_tn.json"
RAW_CSV_PATH = ROOT / "tests" / "fixtures" / "tri_tn_raw.csv"

# East TN counties (lowercase for matching)
EAST_TN_COUNTIES = {
    "knox", "sevier", "blount", "greene", "hamblen",
    "hawkins", "washington", "grainger", "sullivan", "cocke", "jefferson", "anderson",
}

# TRI Basic Data typical column names (may vary by year)
FACILITY_COLS = [
    "FACILITY_NAME", "TRIFID", "FACILITY_NAME", "STREET_ADDRESS",
    "CITY", "COUNTY", "STATE_ABBR", "ZIP_CODE", "LATITUDE", "LONGITUDE",
    "NAICS_CODE", "INDUSTRY_NAICS_CODE",
]
CHEM_COLS = ["CHEMICAL_NAME", "CAS_NUMBER", "TOTAL_RELEASE", "ON_SITE_RELEASE_TOTAL"]

# Class 1: flammable, explosive, toxic gas — elevates WARNING to EMERGENCY within 5 mi
CLASS1_KEYWORDS = [
    "ammonia", "chlorine", "hydrogen sulfide", "benzene", "methanol", "hydrogen cyanide",
    "sulfur dioxide", "nitric acid", "hydrochloric acid", "sulfuric acid",
    "ethylene", "propylene", "vinyl", "xylene", "toluene", "formaldehyde",
    "acetylene", "hydrazine", "ozone", "phosgene", "arsine", "phosphine",
    "styrene", "flammable", "explosive", "toxic gas", "pbt", "dioxin",
]


def _is_class1_chemical(chem: str) -> bool:
    c = (chem or "").lower()
    return any(k in c for k in CLASS1_KEYWORDS)


def fetch_tri_bulk() -> list[dict] | None:
    """Try to fetch TRI TN data from EPA. Returns rows or None."""
    import urllib.request
    urls = [
        "https://www.epa.gov/sites/default/files/2024-03/tri_2022_tn.csv",
        "https://echodata.epa.gov/echo/tri_rest_services.get_facilities?output=JSON&state=TN",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "GAIA-TRI/1.0", "Accept": "text/csv,application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if url.endswith(".csv"):
                return list(csv.DictReader(data.decode("utf-8", errors="replace").splitlines()))
            # JSON would need different parsing
        except Exception as e:
            print(f"  fetch {url}: {e}", file=sys.stderr)
    return None


def _normalize_epa_row(row: dict) -> dict:
    """Normalize EPA 2024 format headers (e.g. '7. COUNTY' -> 'COUNTY')."""
    out = {}
    for k, v in row.items():
        key = k.strip()
        if key and key[0].isdigit() and ". " in key:
            key = key.split(". ", 1)[-1].strip()
        out[key] = v
        # Aliases for common variants
        if "COUNTY" in key.upper() and "COUNTY" not in out:
            out["COUNTY"] = v
        if "ST" == key or "STATE" in key.upper():
            out["ST"] = v
        if "FACILITY" in key.upper() and "NAME" in key.upper():
            out["FACILITY_NAME"] = v
        if "TRIFD" in key.upper() or "TRIFID" in key.upper():
            out["TRIFID"] = v
        if "LATITUDE" in key.upper():
            out["LATITUDE"] = v
        if "LONGITUDE" in key.upper():
            out["LONGITUDE"] = v
        if "STREET" in key.upper():
            out["STREET_ADDRESS"] = v
        if key == "CITY":
            out["CITY"] = v
        if "NAICS" in key.upper():
            out.setdefault("NAICS_CODE", v)
        if key == "CHEMICAL":  # 37. CHEMICAL only, not CLEAN AIR ACT CHEMICAL
            out["CHEMICAL"] = v
        if key == "TOTAL RELEASES":
            out["TOTAL RELEASES"] = v
        if key == "ON-SITE RELEASE TOTAL":
            out["ON-SITE RELEASE TOTAL"] = v
    return out


def load_from_csv(path: Path) -> list[dict]:
    """Load TRI data from local CSV. Handles EPA 2024 format (n. COLUMN headers)."""
    rows = []
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(_normalize_epa_row(row))
    return rows


def filter_east_tn(rows: list[dict]) -> list[dict]:
    """Filter to East TN counties."""
    out = []
    for r in rows:
        county = (r.get("COUNTY") or r.get("County") or r.get("county") or "").strip().lower()
        if not county:
            continue
        # Handle "KNOX" or "Knox County"
        county_base = county.replace(" county", "").replace(" co", "").strip()
        if county_base in EAST_TN_COUNTIES:
            out.append(r)
    return out


def _facility_key(row: dict) -> tuple:
    """Unique key for facility dedup."""
    trifid = (row.get("TRIFID") or row.get("TriFID") or "").strip()
    if trifid:
        return ("trifid", trifid)
    name = (row.get("FACILITY_NAME") or row.get("Facility Name") or "").strip()
    lat = row.get("LATITUDE") or row.get("LAT")
    lon = row.get("LONGITUDE") or row.get("LON")
    return ("loc", name, str(lat), str(lon))


def aggregate_facility_with_chemicals(rows: list[dict]) -> list[dict]:
    """Group by facility, aggregate chemicals, compute has_class1."""
    from collections import defaultdict

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[_facility_key(r)].append(r)

    out = []
    for key, chem_rows in groups.items():
        row = chem_rows[0]
        lat = row.get("LATITUDE") or row.get("Latitude") or row.get("LAT")
        lon = row.get("LONGITUDE") or row.get("Longitude") or row.get("LON")
        try:
            lat_f = float(lat) if lat else None
            lon_f = float(lon) if lon else None
        except (ValueError, TypeError):
            lat_f = lon_f = None

        total_lbs = 0.0
        class1_lbs = 0.0
        top_chemicals = []
        has_class1 = False
        for r in chem_rows:
            chem = (r.get("CHEMICAL") or r.get("CHEMICAL_NAME") or "").strip()
            lbs_val = r.get("TOTAL RELEASES") or r.get("ON-SITE RELEASE TOTAL") or "0"
            try:
                lbs = float(lbs_val) if lbs_val else 0
            except (ValueError, TypeError):
                lbs = 0
            total_lbs += lbs
            if _is_class1_chemical(chem):
                has_class1 = True
                class1_lbs += lbs
            if chem and lbs > 0:
                top_chemicals.append((chem, lbs))

        top_chemicals = sorted(top_chemicals, key=lambda x: -x[1])[:5]
        out.append({
            "name": (row.get("FACILITY_NAME") or row.get("Facility Name") or row.get("FacilityName") or "").strip(),
            "address": (row.get("STREET_ADDRESS") or row.get("Street Address") or "").strip(),
            "city": (row.get("CITY") or row.get("City") or "").strip(),
            "county": (row.get("COUNTY") or row.get("County") or "").strip(),
            "lat": lat_f,
            "lon": lon_f,
            "trifid": (row.get("TRIFID") or row.get("TriFID") or "").strip(),
            "naics": (row.get("NAICS_CODE") or row.get("INDUSTRY_NAICS_CODE") or "").strip(),
            "has_class1": has_class1,
            "class1_lbs": round(class1_lbs, 1),
            "total_lbs": round(total_lbs, 1),
            "top_chemicals": [{"name": c[0], "lbs": round(c[1], 1)} for c in top_chemicals],
        })
    return out


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Populate TRI fixture for East TN")
    parser.add_argument("--input", "-i", type=Path, help="Input CSV (e.g. EPA 2024_us.csv); filter to TN")
    args = parser.parse_args()

    print("Populating TRI fixture for East TN...")

    rows = fetch_tri_bulk()
    if not rows:
        input_path = args.input or RAW_CSV_PATH
        if input_path.exists():
            print("  Using local", input_path)
            rows = load_from_csv(input_path)
            # Filter to Tennessee if US-wide file
            if args.input or "tri_tn_raw" not in str(input_path):
                tn_rows = [r for r in rows if (r.get("ST") or "").strip().upper() == "TN"]
                if tn_rows:
                    print("  Filtered to", len(tn_rows), "TN rows (from", len(rows), "total)")
                    rows = tn_rows
    if not rows:
        print("  No TRI data fetched. Using seed (4 known East TN facilities) for structure.")
        print("  For full TRI: Download TN from epa.gov TRI Basic Data, save as", RAW_CSV_PATH)
        seed = [
            {"name": "EASTMAN CHEMICAL COMPANY, TENNESSEE OPERATIONS", "city": "Kingsport", "county": "Sullivan", "lat": 36.52, "lon": -82.56, "trifid": "37662TNNSSEASTM", "naics": "325211", "address": "100 Eastman Road"},
            {"name": "DOMTAR PAPERS LLC", "city": "Kingsport", "county": "Sullivan", "lat": 36.49, "lon": -82.54, "trifid": "", "naics": "322121", "address": "700 James Blair Drive"},
            {"name": "Y-12 NATIONAL SECURITY COMPLEX", "city": "Oak Ridge", "county": "Anderson", "lat": 35.98, "lon": -84.25, "trifid": "", "naics": "336992", "address": "Building 9212"},
            {"name": "KUB WALTERS WASTEWATER PLANT", "city": "Knoxville", "county": "Knox", "lat": 35.94, "lon": -83.96, "trifid": "", "naics": "221320", "address": "2700 Martin Mill Pike"},
        ]
        FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        out = {"source": "seed_illustrative", "count": len(seed), "facilities": seed}
        FIXTURE_PATH.write_text(json.dumps(out, indent=2))
        print("Wrote", len(seed), "seed facilities to", FIXTURE_PATH)
        for f in seed:
            print("  -", f["name"], "|", f["city"], f["county"])
        return

    east_tn = filter_east_tn(rows)
    facilities = aggregate_facility_with_chemicals(east_tn)

    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "source": "tri_basic_data" if rows else "manual",
        "count": len(facilities),
        "facilities": sorted(facilities, key=lambda f: (f.get("county", ""), f.get("name", ""))),
    }
    FIXTURE_PATH.write_text(json.dumps(out, indent=2))
    print("Wrote", len(facilities), "TRI facilities to", FIXTURE_PATH)
    for fc in facilities[:15]:
        print("  -", fc.get("name"), "|", fc.get("city"), fc.get("county"))
    if len(facilities) > 15:
        print("  ... and", len(facilities) - 15, "more")


if __name__ == "__main__":
    main()
