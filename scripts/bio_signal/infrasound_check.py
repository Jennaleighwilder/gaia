#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DATA_DIR = ROOT / "data" / "bio_signal"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = DATA_DIR / "infrasound_check.json"
USER_AGENT = "GAIA-Research/1.0 (theforgottencode780@gmail.com)"


def http_get(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def main() -> int:
    print("=== CTBTO/IRIS INFRASOUND STATION DATA ===")
    print("Checking availability of infrasound data near tornado corridor...")
    print()

    station_query_url = (
        "https://service.iris.edu/fdsnws/station/1/query?"
        + urllib.parse.urlencode({"network": "IM", "station": "IS10", "format": "text", "level": "station"})
    )
    status_station, body_station = http_get(station_query_url)
    print("Querying IRIS for IS10 station info...")
    print(f"URL: {station_query_url}")
    print(f"FDSN station query status: {status_station}")
    if body_station:
        print(body_station[:300])
    else:
        print("No direct station rows returned for IM/IS10 via FDSN station service.")

    broad_station_url = (
        "https://service.iris.edu/fdsnws/station/1/query?"
        + urllib.parse.urlencode({"network": "IM", "format": "text", "level": "station"})
    )
    status_broad, body_broad = http_get(broad_station_url)
    has_is10_in_broad = "|IS10|" in body_broad or "IS10" in body_broad

    print()
    print("Checking MDA metadata page for IS10...")
    mda_url = "https://ds.iris.edu/mda/IM/IS10/"
    status_mda, body_mda = http_get(mda_url)
    print(f"MDA status: {status_mda}")
    print(body_mda[:300])

    avail_url = (
        "https://service.iris.edu/fdsnws/availability/1/query?"
        + urllib.parse.urlencode(
            {
                "network": "IM",
                "station": "IS10",
                "starttime": "2023-03-22T00:00:00",
                "endtime": "2023-03-25T00:00:00",
                "format": "text",
            }
        )
    )
    print()
    print("Checking infrasound data availability for Rolling Fork date...")
    status_avail, body_avail = http_get(avail_url)
    print(f"Availability status: {status_avail}")
    print(body_avail[:300])

    payload = {
        "station_query": {
            "url": station_query_url,
            "status": status_station,
            "body_preview": body_station[:1000],
        },
        "broad_im_station_listing": {
            "url": broad_station_url,
            "status": status_broad,
            "contains_is10": has_is10_in_broad,
        },
        "mda_page": {
            "url": mda_url,
            "status": status_mda,
            "contains_is10": "MDA : IM : IS10" in body_mda,
            "body_preview": body_mda[:1000],
        },
        "rolling_fork_availability": {
            "url": avail_url,
            "status": status_avail,
            "body_preview": body_avail[:1000],
        },
    }
    with RESULT_PATH.open("w") as f:
        json.dump(payload, f, indent=2)
    print()
    print(f"Saved to {RESULT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
