#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DATA_DIR = ROOT / "data" / "holler_siren"
PILOT_PATH = DATA_DIR / "tfi_v5_yancey_mitchell.json"
WESTERN_PATH = DATA_DIR / "tfi_v5_western_nc.json"
USER_AGENT = "HollerSiren/1.0"
PILOT_BBOX = "-82.38,35.82,-81.82,36.12"
WFS_URL = "https://sdmdataaccess.sc.egov.usda.gov/Spatial/SDMWGS84Geographic.wfs"
SOIL_RISK = {"A": 0.0, "B": 0.1, "C": 0.2, "D": 0.3, "A/D": 0.15, "B/D": 0.2, "C/D": 0.25}


def point_in_polygon(lat: float, lon: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        yi, xi = ring[i]
        yj, xj = ring[j]
        crosses = ((xi > lon) != (xj > lon)) and (
            lat < (yj - yi) * (lon - xi) / ((xj - xi) + 1e-12) + yi
        )
        if crosses:
            inside = not inside
        j = i
    return inside


def fetch_soil_polygons() -> list[dict]:
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "mapunitpolyextended",
        "bbox": PILOT_BBOX,
    }
    url = f"{WFS_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    xml_bytes = urllib.request.urlopen(req, timeout=180).read()
    ns = {
        "ms": "http://mapserver.gis.umn.edu/mapserver",
        "gml": "http://www.opengis.net/gml",
    }
    root = ET.fromstring(xml_bytes)
    polygons = []
    for feature in root.findall(".//ms:mapunitpolyextended", ns):
        hydgrp = (feature.findtext("ms:hydgrpdcd", default="", namespaces=ns) or "").strip() or "B"
        mukey = (feature.findtext("ms:mukey", default="", namespaces=ns) or "").strip()
        coord_nodes = [node for node in feature.findall(".//gml:coordinates", ns) if node.text]
        if not coord_nodes:
            continue
        # The first coordinates node is often just a 2-point envelope.
        # Use the longest coordinate sequence, which carries the actual polygon ring.
        coords_text = max(coord_nodes, key=lambda node: len(node.text.strip().split())).text.strip()
        ring = []
        for pair in coords_text.split():
            lat_str, lon_str = pair.split(",")
            ring.append([float(lat_str), float(lon_str)])
        if not ring:
            continue
        lats = [p[0] for p in ring]
        lons = [p[1] for p in ring]
        polygons.append(
            {
                "mukey": mukey,
                "hydgrp": hydgrp,
                "risk": SOIL_RISK.get(hydgrp, 0.1),
                "bbox": [min(lons), min(lats), max(lons), max(lats)],
                "ring": ring,
            }
        )
    return polygons


def assign(cells: list[dict], polygons: list[dict]) -> tuple[list[dict], int]:
    updated = []
    matched = 0
    for cell in cells:
        lat = float(cell["lat"])
        lon = float(cell["lon"])
        match = None
        for polygon in polygons:
            west, south, east, north = polygon["bbox"]
            if not (west <= lon <= east and south <= lat <= north):
                continue
            if point_in_polygon(lat, lon, polygon["ring"]):
                match = polygon
                break
        updated_cell = cell.copy()
        if match is not None:
            updated_cell["soil_hydgrp"] = match["hydgrp"]
            updated_cell["soil_risk"] = round(float(match["risk"]), 3)
            updated_cell["soil_mukey"] = match["mukey"]
            matched += 1
        updated.append(updated_cell)
    return updated, matched


def main() -> int:
    print("=== FIX 3: SOIL SPATIAL JOIN ===")
    polygons = fetch_soil_polygons()
    print(f"Soil polygons with geometry: {len(polygons)}")

    with PILOT_PATH.open() as f:
        pilot = json.load(f)
    pilot_updated, matched = assign(pilot["cells"], polygons)
    pilot["cells"] = pilot_updated
    pilot["data_layers_included"] = sorted(set(pilot.get("data_layers_included", []) + ["soil_hydgrp"]))
    with PILOT_PATH.open("w") as f:
        json.dump(pilot, f)

    with WESTERN_PATH.open() as f:
        western = json.load(f)
    western_cells = western["cells"]
    updated_western = []
    pilot_index = {(cell["lat"], cell["lon"]): cell for cell in pilot_updated}
    western_matched = 0
    for cell in western_cells:
        key = (cell["lat"], cell["lon"])
        if key in pilot_index:
            updated_western.append({**cell, **{k: v for k, v in pilot_index[key].items() if k.startswith("soil_")}})
            if "soil_mukey" in pilot_index[key]:
                western_matched += 1
        else:
            updated_western.append(cell)
    western["cells"] = updated_western
    western["data_layers_included"] = sorted(set(western.get("data_layers_included", []) + ["soil_hydgrp"]))
    with WESTERN_PATH.open("w") as f:
        json.dump(western, f)

    groups = Counter(cell.get("soil_hydgrp", "UNKNOWN") for cell in pilot_updated if "soil_mukey" in cell)
    print(f"Soil risk assigned to {len(pilot_updated)} pilot cells")
    print(f"Cells with real hydrologic group data: {matched}")
    print(f"Group distribution: {dict(groups)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
