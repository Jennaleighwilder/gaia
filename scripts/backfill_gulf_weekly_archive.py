#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.ingest.weekly_oisst_archive import WeeklyOISSTArchive

RUNS = ROOT / "runs"
REPORT_PATH = RUNS / "gulf_backfill_report.txt"
REPORT_JSON_PATH = RUNS / "gulf_backfill_report.json"
CACHE_DIR = ROOT / "data" / "cache" / "gulf_weekly"


def cached_weeks_for_year(client: WeeklyOISSTArchive, year: int) -> int:
    count = 0
    for week in range(1, client.weeks_in_year(year) + 1):
        if client._cache_path(year, week).exists():
            count += 1
    return count


def main() -> int:
    RUNS.mkdir(exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    buf = StringIO()

    def pr(line: str = "") -> None:
        print(line)
        buf.write(line + "\n")

    client = WeeklyOISSTArchive(use_network=True)
    years = list(range(1990, datetime.now().year + 1))
    summary: dict[str, dict[str, int | bool]] = {}

    pr("=== GULF WEEKLY BACKFILL ===")
    for year in years:
        total_weeks = client.weeks_in_year(year)
        before = cached_weeks_for_year(client, year)
        fetched = 0
        failures = 0
        if before < total_weeks:
            try:
                client.fetch_iso_year_archive(year)
            except Exception:
                pass
        mid = cached_weeks_for_year(client, year)
        fetched += max(0, mid - before)
        for week in range(1, total_weeks + 1):
            cache_path = client._cache_path(year, week)
            if cache_path.exists():
                continue
            rec = client.get_week_anomaly(year, week)
            if cache_path.exists() and not str(rec.get("source", "")).startswith("err:"):
                fetched += 1
            else:
                failures += 1
        after = cached_weeks_for_year(client, year)
        summary[str(year)] = {
            "weeks_total": total_weeks,
            "weeks_before": before,
            "weeks_after": after,
            "fetched": fetched,
            "failures": failures,
            "complete": after == total_weeks,
        }
        pr(
            f"{year}: before={before}/{total_weeks} fetched={fetched} "
            f"after={after}/{total_weeks} failures={failures}"
        )

    complete_years = [int(year) for year, info in summary.items() if info["complete"]]
    payload = {
        "cached_years_complete": complete_years,
        "n_years_complete": len(complete_years),
        "year_summary": summary,
    }
    REPORT_PATH.write_text(buf.getvalue())
    REPORT_JSON_PATH.write_text(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
