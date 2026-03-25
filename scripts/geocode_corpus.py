#!/usr/bin/env python3
"""Geocode master corpus events using Census county centroids.

Reads state+county from events, maps to lat/lon via 2020 Census Gazetteer,
and writes the updated corpus back. Only touches events that lack coordinates.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CENTROIDS_PATH = ROOT / "data" / "county_centroids.txt"
CORPUS_PATH = ROOT / "tests" / "fixtures" / "master_validation_corpus.json"

STATE_ABBREV = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
    "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
    "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
    "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
    "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
    "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN",
    "MISSISSIPPI": "MS", "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE",
    "NEVADA": "NV", "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM", "NEW YORK": "NY", "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK", "OREGON": "OR",
    "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT",
    "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY",
    "DISTRICT OF COLUMBIA": "DC", "PUERTO RICO": "PR",
    "AMERICAN SAMOA": "AS", "GUAM": "GU", "VIRGIN ISLANDS": "VI",
    "NORTHERN MARIANA ISLANDS": "MP",
}

_STRIP_SUFFIXES = re.compile(
    r"\s+(county|parish|borough|census area|municipality|city and borough|city)$",
    re.IGNORECASE,
)


def load_centroids() -> dict[tuple[str, str], tuple[float, float]]:
    """Return {(state_abbrev, county_name_upper): (lat, lon)}."""
    lookup: dict[tuple[str, str], tuple[float, float]] = {}
    for line in CENTROIDS_PATH.read_text().strip().split("\n")[1:]:
        parts = line.split("\t")
        if len(parts) < 10:
            continue
        state_abbrev = parts[0].strip().upper()
        raw_name = parts[3].strip().upper()
        name = _STRIP_SUFFIXES.sub("", raw_name).strip()
        try:
            lat = float(parts[8].strip())
            lon = float(parts[9].strip())
        except (ValueError, IndexError):
            continue
        lookup[(state_abbrev, name)] = (lat, lon)
        # Also store with "ST." variant
        if "SAINT " in name:
            lookup[(state_abbrev, name.replace("SAINT ", "ST. "))] = (lat, lon)
        if "ST. " in name:
            lookup[(state_abbrev, name.replace("ST. ", "SAINT "))] = (lat, lon)
    return lookup


_DIRECTIONAL = re.compile(
    r"^(EAST(?:ERN)?|WEST(?:ERN)?|NORTH(?:ERN)?|SOUTH(?:ERN)?|CENTRAL|UPPER|LOWER|INNER|OUTER)\s+",
    re.IGNORECASE,
)


def normalize_county(county_raw: str) -> str:
    """Extract first county from multi-county strings like 'KNOX AND ANDERSON'."""
    c = county_raw.upper().strip()
    for sep in [",", " AND ", "/", ";", " & "]:
        if sep in c:
            c = c.split(sep)[0].strip()
    c = _STRIP_SUFFIXES.sub("", c).strip()
    return c


def fuzzy_county_candidates(county_raw: str) -> list[str]:
    """Generate fuzzy lookup candidates by stripping directional prefixes."""
    base = normalize_county(county_raw)
    candidates = [base]
    stripped = _DIRECTIONAL.sub("", base).strip()
    if stripped and stripped != base:
        candidates.append(stripped)
        # Strip again for double-prefix like "NORTH EAST FOO"
        stripped2 = _DIRECTIONAL.sub("", stripped).strip()
        if stripped2 and stripped2 != stripped:
            candidates.append(stripped2)
    # Handle possessive/abbreviation patterns
    for c in list(candidates):
        if "CO PLAINS" in c or "CO " in c:
            candidates.append(c.split("CO")[0].strip())
        if " FOOTHILLS" in c:
            candidates.append(c.replace(" FOOTHILLS", "").strip())
        if " MOUNTAINS" in c:
            candidates.append(c.replace(" MOUNTAINS", "").strip())
        if " MOUNTAIN" in c:
            candidates.append(c.replace(" MOUNTAIN", "").strip())
        if " RANGE" in c:
            candidates.append(c.replace(" RANGE", "").strip())
        if " BASIN" in c:
            candidates.append(c.replace(" BASIN", "").strip())
        if " VALLEY" in c:
            candidates.append(c.replace(" VALLEY", "").strip())
        if " HILLS" in c:
            candidates.append(c.replace(" HILLS", "").strip())
        if " PLAINS" in c:
            candidates.append(c.replace(" PLAINS", "").strip())
        if " COAST" in c or " COASTAL" in c:
            candidates.append(c.replace(" COASTAL", "").replace(" COAST", "").strip())
    return [x for x in dict.fromkeys(candidates) if x]


def main() -> int:
    centroids = load_centroids()
    print(f"Loaded {len(centroids)} county centroids")

    corpus = json.loads(CORPUS_PATH.read_text())
    patched = 0
    missed = 0
    already = 0
    missed_combos: set[tuple[str, str]] = set()

    for e in corpus:
        lat = float(e.get("lat") or 0)
        lon = float(e.get("lon") or 0)
        if lat and lon:
            already += 1
            continue

        state_name = (e.get("state") or "").upper().strip()
        county_raw = e.get("county") or ""
        abbrev = STATE_ABBREV.get(state_name, state_name)
        candidates = fuzzy_county_candidates(county_raw)

        coords = None
        for cand in candidates:
            coords = centroids.get((abbrev, cand))
            if coords:
                break
        if coords:
            e["lat"] = coords[0]
            e["lon"] = coords[1]
            e["geocoded"] = "county_centroid"
            patched += 1
        else:
            missed += 1
            missed_combos.add((abbrev, candidates[0] if candidates else county_raw))

    print(f"Already had lat/lon: {already}")
    print(f"Geocoded (county centroid): {patched}")
    print(f"Could not geocode: {missed} ({len(missed_combos)} unique combos)")

    if missed_combos:
        sample = sorted(missed_combos)[:20]
        print(f"Sample unmatched: {sample}")

    CORPUS_PATH.write_text(json.dumps(corpus, indent=2) + "\n")
    print(f"Updated {CORPUS_PATH}")
    return 0


if __name__ == "__main__":
    exit(main())
