#!/usr/bin/env python3
"""
Verify Copernicus CDS credentials and (optionally) queue a minimal ERA5 retrieve.

Setup (human steps):
  1. Register at https://cds.climate.copernicus.eu
  2. Create ~/.cdsapirc with your API URL and key, e.g.:

     url: https://cds.climate.copernicus.eu/api
     key: <uid>:<api-key>

     (Some docs use https://cds.climate.copernicus.eu/api/v2 — use the URL shown on your profile.)

  3. Accept the licence for ERA5 datasets in the CDS web UI before first download.

Usage:
  python scripts/cds_connection_test.py
  python scripts/cds_connection_test.py --probe-retrieve   # submits a small CDS job (slow)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _read_cdsapirc() -> tuple[bool, str]:
    p = Path.home() / ".cdsapirc"
    if not p.exists():
        return False, f"missing {p}"
    text = p.read_text(encoding="utf-8", errors="replace")
    if "url:" not in text or "key:" not in text:
        return False, ".cdsapirc should contain 'url:' and 'key:' lines"
    return True, str(p)


def main() -> int:
    ap = argparse.ArgumentParser(description="Test CDS / cdsapi configuration")
    ap.add_argument(
        "--probe-retrieve",
        action="store_true",
        help="Submit a minimal derived ERA5 daily job (queues on CDS; can take minutes)",
    )
    args = ap.parse_args()

    ok, msg = _read_cdsapirc()
    print(f"~/.cdsapirc: {msg}")
    if not ok:
        print("CDS config: FAIL")
        return 1

    try:
        import cdsapi
    except ImportError:
        print("cdsapi: not installed (pip install 'cdsapi>=0.7.7')")
        return 1

    try:
        client = cdsapi.Client()
    except Exception as e:
        print(f"cdsapi.Client(): FAIL ({e})")
        return 1

    print("cdsapi.Client(): OK (credentials loaded)")

    if not args.probe_retrieve:
        print("CDS connection: OK (no retrieve attempted; use --probe-retrieve to exercise the API)")
        return 0

    import tempfile

    from runtime.ingest.era5_daily_ao import DATASET_DAILY, era5_cds_temp_parent

    req = {
        "product_type": "reanalysis",
        "variable": ["geopotential"],
        "year": "2011",
        "month": ["01"],
        "day": ["01"],
        "pressure_level": ["1000"],
        "daily_statistic": "daily_mean",
        "time_zone": "utc+00:00",
        "frequency": "1_hourly",
        "area": [90, -180, 20, 180],
    }
    try:
        with tempfile.TemporaryDirectory(dir=str(era5_cds_temp_parent())) as td:
            target = Path(td) / "probe"
            print("Submitting minimal CDS retrieve (2011-01-01, 1000 hPa Z)...")
            client.retrieve(DATASET_DAILY, req, str(target))
            out = list(Path(td).iterdir())
            if not out:
                print("probe retrieve: FAIL (no output file)")
                return 1
            print(f"probe retrieve: OK (wrote {out[0].name})")
    except Exception as e:
        print(f"probe retrieve: FAIL ({e})")
        return 1

    print("CDS end-to-end: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
