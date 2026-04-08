#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
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
RESULT_PATH = DATA_DIR / "movebank_studies.json"
MOVEBANK_BASE = "https://www.movebank.org/movebank/service/direct-read"
USER_AGENT = "GAIA-Research/1.0 (theforgottencode780@gmail.com)"

KEYWORDS = [
    "bird",
    "warbler",
    "thrush",
    "sparrow",
    "hawk",
    "migration",
    "deer",
    "elk",
    "bat",
    "songbird",
    "raptor",
    "owl",
    "tennessee",
    "kentucky",
    "mississippi",
    "alabama",
    "arkansas",
    "southeast",
    "appalachia",
    "carolina",
]


def http_get(url: str) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/csv",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def movebank_query(params: dict[str, str]) -> tuple[int, str, str]:
    url = f"{MOVEBANK_BASE}?{urllib.parse.urlencode(params)}"
    status, body = http_get(url)
    return status, body, url


def filter_relevant(studies: list[dict]) -> list[dict]:
    keep: list[dict] = []
    for study in studies:
        haystack = " ".join(
            [
                study.get("name", ""),
                study.get("study_objective", ""),
                study.get("principal_investigator_name", ""),
                study.get("taxon_ids", ""),
                study.get("main_location_lat", ""),
                study.get("main_location_long", ""),
            ]
        ).lower()
        if any(keyword in haystack for keyword in KEYWORDS):
            keep.append(study)
    return keep


def main() -> int:
    print("=== MOVEBANK / ICARUS ANIMAL TRACKING DATA ===")
    print()
    print("Searching for public studies in SE United States...")

    attempts = [
        {
            "name": "documented_public_download_access",
            "params": {"entity_type": "study", "i_have_download_access": "true"},
        },
        {
            "name": "documented_public_view_access",
            "params": {"entity_type": "study", "i_can_see_data": "true"},
        },
        {
            "name": "prompt_query_shape",
            "params": {
                "entity_type": "study",
                "i_am_owner": "false",
                "there_are_data_which_i_may_see": "true",
            },
        },
        {
            "name": "plain_study_listing",
            "params": {"entity_type": "study"},
        },
    ]

    output = {
        "source": "Movebank direct-read API",
        "docs_url": "https://www.movebank.org/cms/movebank-api",
        "api_reference": "https://github.com/movebank/movebank-api-doc/blob/master/movebank-api.md",
        "attempts": [],
        "relevant_studies": [],
    }

    studies: list[dict] = []
    for attempt in attempts:
        status, body, url = movebank_query(attempt["params"])
        preview = body[:500]
        record = {
            "attempt": attempt["name"],
            "url": url,
            "status": status,
            "body_preview": preview,
        }
        output["attempts"].append(record)
        print(f"  {attempt['name']}: HTTP {status}")
        if status == 200 and not body.lstrip().startswith("<!doctype html"):
            reader = csv.DictReader(io.StringIO(body))
            studies = list(reader)
            print(f"    Parsed {len(studies)} studies")
            break
        if status in (401, 403):
            print("    Access blocked by live service")

    if studies:
        relevant = filter_relevant(studies)
        output["relevant_studies"] = relevant
        print(f"Total public studies returned: {len(studies)}")
        print(f"Potentially relevant studies: {len(relevant)}")
        print()
        print("Top relevant studies:")
        for study in relevant[:20]:
            print(f"  ID: {study.get('id', 'N/A')}")
            print(f"  Name: {study.get('name', 'N/A')[:80]}")
            print(f"  PI: {study.get('principal_investigator_name', 'N/A')}")
            print(f"  Taxa: {study.get('taxon_ids', 'N/A')[:60]}")
            print()
    else:
        print("Could not obtain a public-study listing from the live Movebank service.")
        print("The current direct-read endpoint returned authentication errors for anonymous queries.")

    with RESULT_PATH.open("w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved Movebank study result to {RESULT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
