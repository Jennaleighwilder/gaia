#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


OUTPUT_DIR = ROOT / "data" / "holler_siren"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ITEM_ID = "674634a1d34e6d1dac3abddc"
ITEM_URL = f"https://www.sciencebase.gov/catalog/item/{ITEM_ID}?format=json"
INVENTORY_PATH = OUTPUT_DIR / "helene_landslides.csv"
USER_AGENT = "HollerSiren/1.0 (theforgottencode780@gmail.com)"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", errors="replace")


def choose_download(item: dict) -> tuple[str | None, str | None]:
    files = item.get("files", [])
    print(f"Files available: {len(files)}")
    for entry in files:
        print(f"  {entry.get('name', 'N/A')} - {float(entry.get('size', 0))/1e6:.1f} MB")

    for entry in files:
        name = entry.get("name", "").lower()
        if name.endswith(".csv"):
            return entry.get("downloadUri") or entry.get("url"), "csv"
    for entry in files:
        name = entry.get("name", "").lower()
        if name.endswith(".geojson"):
            return entry.get("downloadUri") or entry.get("url"), "geojson"
    return None, None


def convert_geojson_to_csv(content: str, out_path: Path) -> int:
    geojson = json.loads(content)
    features = geojson.get("features", [])
    rows: list[dict] = []
    for feature in features:
        coords = feature.get("geometry", {}).get("coordinates", [None, None])
        props = feature.get("properties", {})
        rows.append(
            {
                "latitude": coords[1],
                "longitude": coords[0],
                "source": props.get("Source", ""),
                "impact": props.get("Impact", ""),
            }
        )

    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["latitude", "longitude", "source", "impact"])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> int:
    if INVENTORY_PATH.exists():
        print(f"Inventory already cached: {INVENTORY_PATH}")
    else:
        print("Downloading USGS Helene landslide inventory...")
        item = fetch_json(ITEM_URL)
        download_url, kind = choose_download(item)

        if not download_url:
            raise SystemExit("No CSV or GeoJSON download URI found in ScienceBase item metadata")

        print(f"Using {kind.upper()} download: {download_url}")
        content = fetch_text(download_url)
        if kind == "csv":
            INVENTORY_PATH.write_text(content, encoding="utf-8")
            print(f"Downloaded {len(content)} bytes")
        else:
            count = convert_geojson_to_csv(content, INVENTORY_PATH)
            print(f"Converted GeoJSON to CSV with {count} rows")

    with INVENTORY_PATH.open() as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"\nInventory loaded: {len(rows)} landslide points")
    print(f"Columns: {list(rows[0].keys()) if rows else 'none'}")
    if rows:
        for row in rows[:3]:
            lat = row.get("latitude") or row.get("y") or row.get("lat")
            lon = row.get("longitude") or row.get("x") or row.get("lon")
            impact = row.get("impact") or row.get("Impact") or ""
            print(f"  lat={lat} lon={lon} impact={impact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
