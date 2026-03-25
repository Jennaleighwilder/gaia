#!/usr/bin/env python3
"""Merge validation JSON corpora into master_validation_corpus.json with dedup by event_id."""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_FILES = [
    "tests/fixtures/major_events_1950_present.json",
    "tests/fixtures/major_events_1996_2025.json",
    "tests/fixtures/landmark_events.json",
    "tests/fixtures/national_validation/ok_ef2plus_tornadoes.json",
    "tests/fixtures/national_validation/ca_wildfires.json",
    "tests/fixtures/national_validation/flood_events.json",
    "tests/fixtures/national_validation_corpus.json",
]


def iter_payloads(data):
    if isinstance(data, list):
        yield from data
    elif isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, list):
                yield from val


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--output",
        type=Path,
        default=ROOT / "tests/fixtures/master_validation_corpus.json",
    )
    ap.add_argument("extra_files", nargs="*", help="Additional JSON paths (optional)")
    args = ap.parse_args()

    files = [ROOT / f for f in DEFAULT_FILES] + [Path(p) for p in args.extra_files]
    all_events: list[dict] = []
    for f in files:
        if not f.is_absolute():
            f = ROOT / f
        if not f.exists():
            try:
                disp = f.relative_to(ROOT)
            except ValueError:
                disp = f
            print(f"Missing: {disp}")
            continue
        data = json.loads(f.read_text())
        all_events.extend(iter_payloads(data))

    seen: set[str] = set()
    unique: list[dict] = []
    for e in all_events:
        eid = e.get("event_id") or e.get("id")
        if not eid:
            eid = f"{e.get('date', '')}_{e.get('county', '')}_{e.get('event_type', '')}_{len(unique)}"
        eid = str(eid)
        if eid in seen:
            continue
        seen.add(eid)
        unique.append(e)

    by_type = collections.Counter((e.get("event_type") or "unknown") for e in unique)
    print(f"Total unique events: {len(unique)}")
    print("By type (top 20):")
    for k, v in by_type.most_common(20):
        print(f"  {k}: {v}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(unique, indent=2))
    print(f"Saved -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
