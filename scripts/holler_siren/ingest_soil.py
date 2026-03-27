#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "holler_siren"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SOIL_URL = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"
SOIL_WFS = "https://sdmdataaccess.sc.egov.usda.gov/Spatial/SDMWGS84Geographic.wfs"
USER_AGENT = "HollerSiren/1.0 (theforgottencode780@gmail.com)"
PILOT_AREA_SYMBOLS = ("NC199", "NC121")
FULL_WESTERN_BBOX = (-84.3, 35.0, -81.8, 36.6)  # west, south, east, north

SOIL_CACHE = DATA_DIR / "statsgo_soil.json"
SOIL_POLY_CACHE = DATA_DIR / "statsgo_soil_polygons.json"


def fetch_tabular_soil() -> dict:
    if SOIL_CACHE.exists():
        with SOIL_CACHE.open() as f:
            return json.load(f)

    query = """SELECT co.areasymbol, co.areaname,
           mapunit.mukey, mapunit.muname,
           component.compname, component.hydgrp,
           component.comppct_r, muaggatt.hydgrpdcd
    FROM legend
    INNER JOIN mapunit ON mapunit.lkey = legend.lkey
    INNER JOIN muaggatt ON muaggatt.mukey = mapunit.mukey
    LEFT JOIN component ON component.mukey = mapunit.mukey
        AND component.majcompflag = 'Yes'
    INNER JOIN sacatalog co ON co.areasymbol = legend.areasymbol
    WHERE legend.areasymbol IN ('NC199', 'NC121')
    ORDER BY mapunit.mukey"""
    payload = json.dumps({"query": query, "FORMAT": "JSON+COLUMNNAME"}).encode()
    req = urllib.request.Request(
        SOIL_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    with SOIL_CACHE.open("w") as f:
        json.dump(data, f)
    return data


def parse_tabular_soil(data: dict) -> dict[str, dict]:
    rows = data.get("Table", [])
    if not rows:
        return {}
    headers = rows[0]
    hydgrp_map = {"A": 0.0, "B": 0.1, "C": 0.2, "D": 0.3, "A/D": 0.15, "B/D": 0.2, "C/D": 0.25}
    by_mukey: dict[str, dict] = {}
    for row in rows[1:]:
        record = dict(zip(headers, row))
        mukey = str(record.get("mukey", "")).strip()
        hydgrp = str(record.get("hydgrpdcd") or record.get("hydgrp") or "B").strip()
        if mukey:
            by_mukey[mukey] = {
                "hydgrp": hydgrp,
                "risk": hydgrp_map.get(hydgrp, 0.1),
                "muname": record.get("muname"),
                "areasymbol": record.get("areasymbol"),
            }
    return by_mukey


def fetch_polygon_soil() -> dict:
    if SOIL_POLY_CACHE.exists():
        with SOIL_POLY_CACHE.open() as f:
            return json.load(f)

    ns = {
        "gml": "http://www.opengis.net/gml",
        "ms": "http://mapserver.gis.umn.edu/mapserver",
    }
    polygons: list[dict] = []
    west, south, east, north = FULL_WESTERN_BBOX
    tile_size = 0.8
    seen = set()

    tile_west = west
    while tile_west < east:
        tile_south = south
        tile_east = min(east, tile_west + tile_size)
        while tile_south < north:
            tile_north = min(north, tile_south + tile_size)
            params = {
                "service": "WFS",
                "version": "1.1.0",
                "request": "GetFeature",
                "typeName": "mapunitpolyextended",
                "bbox": f"{tile_west},{tile_south},{tile_east},{tile_north}",
            }
            url = f"{SOIL_WFS}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=180) as resp:
                xml_bytes = resp.read()
            root = ET.fromstring(xml_bytes)

            for feature in root.findall(".//ms:mapunitpolyextended", ns):
                props = {}
                coords_text = None
                for child in feature:
                    tag = child.tag.split("}")[-1]
                    if tag == "multiPolygon":
                        coords_node = child.find(".//gml:coordinates", ns)
                        coords_text = coords_node.text if coords_node is not None else None
                        continue
                    props[tag] = (child.text or "").strip()
                if not coords_text:
                    continue
                points = []
                for pair in coords_text.strip().split():
                    lat_str, lon_str = pair.split(",")
                    points.append((float(lat_str), float(lon_str)))
                if not points:
                    continue
                mukey = props.get("mukey", "")
                first_point = points[0]
                dedupe_key = (mukey, round(first_point[0], 5), round(first_point[1], 5))
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                lats = [p[0] for p in points]
                lons = [p[1] for p in points]
                polygons.append(
                    {
                        "mukey": mukey,
                        "hydgrpdcd": props.get("hydgrpdcd", ""),
                        "muname": props.get("muname", ""),
                        "bbox": [min(lons), min(lats), max(lons), max(lats)],
                        "ring": [[round(lat, 6), round(lon, 6)] for lat, lon in points],
                    }
                )
            tile_south = tile_north
        tile_west = tile_east

    payload = {"bbox": FULL_WESTERN_BBOX, "polygons": polygons}
    with SOIL_POLY_CACHE.open("w") as f:
        json.dump(payload, f)
    return payload


def main() -> int:
    print("=== STEP 1: STATSGO SOIL DATA ===")
    tabular = fetch_tabular_soil()
    soil_by_mukey = parse_tabular_soil(tabular)
    print(f"Soil map units parsed: {len(soil_by_mukey)}")
    if soil_by_mukey:
        groups = Counter(row["hydgrp"] for row in soil_by_mukey.values())
        print(f"Hydrologic groups: {dict(groups)}")

    try:
        poly_data = fetch_polygon_soil()
        print(f"Soil polygons cached for full western NC: {len(poly_data.get('polygons', []))}")
    except Exception as exc:
        print(f"Soil polygon WFS failed: {exc}")
        with SOIL_POLY_CACHE.open("w") as f:
            json.dump({"bbox": FULL_WESTERN_BBOX, "polygons": []}, f)

    print(f"Saved tabular soil cache to {SOIL_CACHE}")
    print(f"Saved polygon soil cache to {SOIL_POLY_CACHE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
