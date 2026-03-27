#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PNA_URLS = [
    "https://ftp.cpc.ncep.noaa.gov/cwlinks/para/norm.daily.pna.index.b500101.current.ascii",
    "https://www.cpc.noaa.gov/products/precip/CWlink/daily_ao_index/pna/daily.pna.index.b500101.current.ascii",
]
CACHE_PATH = ROOT / "data" / "cache" / "pna_daily_archive.json"


def fetch_text(urls: list[str], timeout: int = 30) -> str:
    last_error: Exception | None = None
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError("no PNA URLs configured")


def parse_pna_ascii(text: str) -> dict[str, float]:
    archive: dict[str, float] = {}
    for line in text.strip().splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            value = float(parts[3])
        except ValueError:
            continue
        if not (-99.0 < value < 99.0):
            continue
        archive[f"{year:04d}-{month:02d}-{day:02d}"] = float(value)
    return archive


def build_and_save_archive() -> dict[str, float]:
    print("Fetching PNA index from NOAA...")
    text = fetch_text(PNA_URLS)
    archive = parse_pna_ascii(text)
    print(f"PNA values parsed: {len(archive)}")
    if archive:
        print(f"Date range: {min(archive)} to {max(archive)}")
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_PATH.open("w") as f:
        json.dump(archive, f, indent=2)
    print(f"Saved to {CACHE_PATH}")
    return archive


def load_pna_archive(fetch_if_missing: bool = True) -> dict[str, float]:
    if CACHE_PATH.exists():
        with CACHE_PATH.open() as f:
            raw = json.load(f)
        return {str(key): float(value) for key, value in raw.items()}
    if not fetch_if_missing:
        return {}
    return build_and_save_archive()


def main() -> int:
    archive = build_and_save_archive()
    if archive:
        sample_dates = sorted(archive)[:3] + sorted(archive)[-2:]
        seen: set[str] = set()
        for ds in sample_dates:
            if ds in seen:
                continue
            seen.add(ds)
            print(f"  {ds}: PNA={archive[ds]:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
