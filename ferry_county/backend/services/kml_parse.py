from __future__ import annotations

import html
import re
import zipfile
from dataclasses import dataclass
from io import BytesIO

from defusedxml.ElementTree import fromstring as xml_fromstring

from backend.services.stable_id import compute_source_feature_id

# Zip / XML bombs: cap uncompressed doc.kml size (Avenza-scale files are ~9MB uncompressed).
MAX_DOC_KML_BYTES = 60 * 1024 * 1024


def _local(tag: str | None) -> str:
    if not tag:
        return ""
    return tag.split("}")[-1] if "}" in tag else tag


def _text(elem) -> str:
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


def _linestring_wkt(coords: list[tuple[float, float]]) -> str:
    inner = ", ".join(f"{lon} {lat}" for lon, lat in coords)
    return f"({inner})"


def _multilinestring_wkt(lines: list[list[tuple[float, float]]]) -> str:
    parts = ", ".join(_linestring_wkt(line) for line in lines)
    return f"MULTILINESTRING ({parts})"


def _parse_coords(coords_el) -> list[tuple[float, float]]:
    if coords_el is None or not coords_el.text:
        return []
    pairs: list[tuple[float, float]] = []
    for token in coords_el.text.strip().split():
        parts = token.split(",")
        if len(parts) >= 2:
            try:
                lon, lat = float(parts[0]), float(parts[1])
                pairs.append((lon, lat))
            except ValueError:
                continue
    return pairs


def _parse_description_meta(desc: str) -> dict[str, str | float | None]:
    raw = html.unescape(desc)
    text_only = re.sub(r"<[^>]+>", " ", raw)
    text_only = re.sub(r"\s+", " ", text_only)
    meta: dict[str, str | float | None] = {}
    m = re.search(r"Road #\s*([0-9A-Za-z\-]+)", text_only, re.I)
    if m:
        meta["road_number"] = m.group(1)
    m = re.search(r"Grant Miles \(CEMP\)[^\d]*([0-9.]+)\s*mi", text_only, re.I)
    if m:
        try:
            meta["cemp_miles"] = float(m.group(1))
        except ValueError:
            meta["cemp_miles"] = None
    m = re.search(r"Road Length[^\d]*([0-9.]+)\s*mi", text_only, re.I)
    if m:
        try:
            meta["length_mi"] = float(m.group(1))
        except ValueError:
            meta["length_mi"] = None
    m = re.search(r"Class[^\w]*([A-Za-z /]+)", text_only)
    if m:
        meta["federal_class"] = m.group(1).strip()
    return meta


@dataclass
class ParsedRoad:
    source_feature_id: str
    road_name: str
    kml_folder_path: str
    is_lapr: bool
    road_number: str | None
    length_mi: float | None
    cemp_miles: float | None
    federal_class: str | None
    geometry_wkt: str


def _parse_kmz_zipfile(zf: zipfile.ZipFile) -> list[ParsedRoad]:
    try:
        info = zf.getinfo("doc.kml")
    except KeyError as e:
        raise ValueError("KMZ must contain doc.kml") from e
    if info.file_size > MAX_DOC_KML_BYTES:
        raise ValueError("doc.kml exceeds maximum allowed size")
    raw = zf.read("doc.kml")
    if len(raw) > MAX_DOC_KML_BYTES:
        raise ValueError("doc.kml exceeds maximum allowed size")
    root = xml_fromstring(raw)
    out: list[ParsedRoad] = []

    def walk(elem, folder_path: str, in_lapr: bool) -> None:
        tag = _local(elem.tag)
        if tag == "Folder":
            name = ""
            for c in elem:
                if _local(c.tag) == "name":
                    name = _text(c)
                    break
            path = f"{folder_path}/{name}" if folder_path else name
            lapr = in_lapr or ("LAPR" in (name or ""))
            for c in elem:
                walk(c, path, lapr)
            return
        if tag == "Placemark":
            road_name = ""
            desc = ""
            line_coords: list[list[tuple[float, float]]] = []
            for c in elem:
                ct = _local(c.tag)
                if ct == "name":
                    road_name = _text(c)
                elif ct == "description":
                    desc = c.text or ""
                elif ct == "LineString":
                    for g in c:
                        if _local(g.tag) == "coordinates":
                            pts = _parse_coords(g)
                            if len(pts) >= 2:
                                line_coords.append(pts)
                elif ct == "MultiGeometry":
                    for g in c:
                        if _local(g.tag) == "LineString":
                            for gg in g:
                                if _local(gg.tag) == "coordinates":
                                    pts = _parse_coords(gg)
                                    if len(pts) >= 2:
                                        line_coords.append(pts)
            if not line_coords:
                return
            wkt = _multilinestring_wkt(line_coords)
            meta = _parse_description_meta(desc)
            sf_id = compute_source_feature_id(folder_path=folder_path, name=road_name, geometry_wkt=wkt)
            out.append(
                ParsedRoad(
                    source_feature_id=sf_id,
                    road_name=road_name or "Unnamed",
                    kml_folder_path=folder_path,
                    is_lapr=in_lapr,
                    road_number=meta.get("road_number") if isinstance(meta.get("road_number"), str) else None,
                    length_mi=float(meta["length_mi"]) if meta.get("length_mi") is not None else None,
                    cemp_miles=float(meta["cemp_miles"]) if meta.get("cemp_miles") is not None else None,
                    federal_class=meta.get("federal_class") if isinstance(meta.get("federal_class"), str) else None,
                    geometry_wkt=wkt,
                )
            )
            return
        for c in elem:
            walk(c, folder_path, in_lapr)

    doc = root
    if _local(root.tag) == "kml":
        for c in root:
            if _local(c.tag) == "Document":
                doc = c
                break
    for c in doc:
        walk(c, "", False)
    return out


def parse_kmz_roads(kmz_path: str) -> list[ParsedRoad]:
    with zipfile.ZipFile(kmz_path, "r") as zf:
        return _parse_kmz_zipfile(zf)


def parse_kmz_bytes(data: bytes) -> list[ParsedRoad]:
    with zipfile.ZipFile(BytesIO(data), "r") as zf:
        return _parse_kmz_zipfile(zf)
