#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.holler_siren.ingest_terrain import query_tnm_products


REGION = "east_tennessee"
BBOX_STR = "-82.45,36.10,-81.65,36.65"  # west,south,east,north


def main() -> int:
    print(f"=== EAST TENNESSEE DEM TEST: {REGION} ===")
    print(f"BBOX: {BBOX_STR}")
    items = query_tnm_products(BBOX_STR)
    print(f"DEM products available: {len(items)}")
    for item in items[:10]:
        title = item.get("title", "?")
        size_mb = round(float(item.get("sizeInBytes", 0)) / 1e6, 1)
        published = item.get("publicationDate", "")
        print(f"  {title} | {size_mb} MB | {published}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
