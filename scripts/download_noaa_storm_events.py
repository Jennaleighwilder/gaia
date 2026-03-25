#!/usr/bin/env python3
"""Download NOAA Storm Events detail CSVs from NCEI SWDI (gzip → decompressed CSV)."""
from __future__ import annotations

import argparse
import gzip
import io
import re
import time
import urllib.request
from pathlib import Path

BASE = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
LIST_RE = re.compile(
    r'href="(StormEvents_details-ftp_v1\.0_d(\d{4})_c\d+\.csv\.gz)"',
    re.I,
)


def list_remote_files() -> list[tuple[str, int]]:
    req = urllib.request.Request(BASE, headers={"User-Agent": "GAIA/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        html = r.read().decode("utf-8", errors="replace")
    out = []
    for m in LIST_RE.finditer(html):
        out.append((m.group(1), int(m.group(2))))
    # de-dupe by fname
    by_name = {fn: yr for fn, yr in out}
    return sorted(by_name.items(), key=lambda x: x[1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path("tests/fixtures/noaa_storm_events"),
        help="Output directory for decompressed .csv files",
    )
    ap.add_argument("--year-min", type=int, default=1950)
    ap.add_argument("--year-max", type=int, default=1995)
    ap.add_argument("--sleep", type=float, default=0.5, help="Seconds between downloads")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    remote = list_remote_files()
    targets = [(fn, yr) for fn, yr in remote if args.year_min <= yr <= args.year_max]
    print(f"Remote index: {len(remote)} detail files; downloading {len(targets)} in [{args.year_min},{args.year_max}]")

    ok = 0
    for fname, yr in targets:
        out_path = args.out_dir / fname.replace(".gz", "")
        if out_path.exists():
            print(f"  {fname}: skip (exists)")
            ok += 1
            continue
        url = BASE + fname
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                gz_data = r.read()
            with gzip.open(io.BytesIO(gz_data), "rb") as gz:
                content = gz.read()
            out_path.write_bytes(content)
            print(f"  {fname}: {len(content) // 1024} KB uncompressed")
            ok += 1
        except Exception as e:
            print(f"  {fname}: ERROR {e}")
        time.sleep(args.sleep)

    print(f"Done: {ok}/{len(targets)} files ready under {args.out_dir}")
    return 0 if ok == len(targets) else 1


if __name__ == "__main__":
    raise SystemExit(main())
