#!/usr/bin/env python3
"""
1) Fetch ERA5 derived daily 1000 hPa heights for every Path 1 La Niña month (104 months).
2) Rebuild one cross-corpus EOF (sign fixed vs polar cap), z-score projections, write
   data/cache/era5_daily_ao/daily_ao_archive.json (ERA5 overwrites; monthly interp fills gaps).

Then run Path 1 daily validation (optional).

  PYTHONUNBUFFERED=1 PYTHONPATH=. python3 -u scripts/era5_la_nina_full_pipeline.py
  PYTHONPATH=. python3 scripts/era5_la_nina_full_pipeline.py --rebuild-only --path1
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.ingest.era5_daily_ao import (  # noqa: E402
    CACHE_DIR,
    ERA5_DAILY_AO_ARCHIVE_PATH,
    ERA5DailyAO,
    la_nina_validation_months,
    rebuild_global_eof_la_nina_archive,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild-only", action="store_true", help="Skip CDS; only EOF + archive")
    ap.add_argument("--no-path1", action="store_true", help="Skip Path 1 daily validation at end")
    args = ap.parse_args()

    months = la_nina_validation_months()
    print(f"La Niña months in corpus: {len(months)}", flush=True)

    failed: list[tuple[int, int, str]] = []
    if not args.rebuild_only:
        ao = ERA5DailyAO()
        ok = 0
        for y, m in months:
            p = CACHE_DIR / f"hgt1000_daily_{y}_{m:02d}.json"
            if p.exists():
                print(f"  {y}-{m:02d} cached", flush=True)
                ok += 1
                continue
            try:
                d = ao.fetch_daily_1000mb_heights(y, m)
                print(f"  {y}-{m:02d} fetched {len(d)} days", flush=True)
                ok += 1
            except Exception as e:
                print(f"  {y}-{m:02d} FAILED {e}", flush=True)
                failed.append((y, m, str(e)))
        print(f"\nDaily months OK: {ok}/{len(months)}", flush=True)
        if failed:
            print(
                f"Failed ({len(failed)}): {failed[:8]}{'...' if len(failed) > 8 else ''}",
                flush=True,
            )

    print("\nRebuilding global EOF + daily_ao_archive.json ...", flush=True)
    n_era5 = rebuild_global_eof_la_nina_archive()
    print(f"  ERA5 AO days written: {len(n_era5)}", flush=True)
    print(f"  -> {ERA5_DAILY_AO_ARCHIVE_PATH}", flush=True)
    print(f"  -> {CACHE_DIR / 'eof_global_la_nina_signfixed.npy'}", flush=True)

    if not args.no_path1:
        print("\nRunning path1_daily_validation.py ...", flush=True)
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "path1_daily_validation.py")],
            cwd=str(ROOT),
            env={**dict(__import__("os").environ), "PYTHONPATH": str(ROOT)},
        )
        return int(r.returncode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
