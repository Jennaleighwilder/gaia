#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bio_signal.common import DATA_DIR, fetch_json, save_json


BASE_URL = "https://dashboard.birdcast.org/api/v1/is-birdcast-alert-api/"
API_KEY = "cfhnnvfh85l6"
RESULT_PATH = DATA_DIR / "birdcast_results.json"

TEST_CASES = [
    {"date": "2021-12-10", "label": "Quad-State eve (outbreak)", "case": "Quad-State", "region": "US-KY"},
    {"date": "2021-12-07", "label": "Dec 7 2021 (quiet)", "case": "Quad-State", "region": "US-KY"},
    {"date": "2021-12-14", "label": "Dec 14 2021 (quiet)", "case": "Quad-State", "region": "US-KY"},
    {"date": "2011-04-27", "label": "Super Outbreak eve", "case": "Super Outbreak", "region": "US-AL"},
    {"date": "2011-04-24", "label": "Apr 24 2011 (quiet)", "case": "Super Outbreak", "region": "US-AL"},
    {"date": "2011-04-30", "label": "Apr 30 2011 (quiet)", "case": "Super Outbreak", "region": "US-AL"},
    {"date": "2023-03-24", "label": "Rolling Fork MS eve", "case": "Rolling Fork", "region": "US-MS"},
    {"date": "2023-03-21", "label": "Mar 21 2023 (quiet)", "case": "Rolling Fork", "region": "US-MS"},
]


def endpoint(path: str, **params: str) -> str:
    query = urllib.parse.urlencode(params)
    return f"{BASE_URL}{path}?{query}"


def summarize_live(data: dict) -> dict:
    night_series = data.get("nightSeries") or []
    if not night_series:
        return {
            "has_data": False,
            "peak_vid": None,
            "mean_vid": None,
            "peak_num_aloft": None,
            "mean_num_aloft": None,
            "cumulative_birds": data.get("cumulativeBirds", 0),
            "is_high": data.get("isHigh", False),
        }
    vids = [row["vid"] for row in night_series if row.get("vid") is not None]
    aloft = [row["numAloft"] for row in night_series if row.get("numAloft") is not None]
    return {
        "has_data": True,
        "peak_vid": round(max(vids), 3) if vids else None,
        "mean_vid": round(sum(vids) / len(vids), 3) if vids else None,
        "peak_num_aloft": int(max(aloft)) if aloft else None,
        "mean_num_aloft": round(sum(aloft) / len(aloft), 1) if aloft else None,
        "cumulative_birds": int(data.get("cumulativeBirds", 0)),
        "is_high": bool(data.get("isHigh", False)),
        "timezone": data.get("timezoneName"),
        "last_updated": data.get("lastUpdated"),
    }


def summarize_hist(data: dict) -> dict:
    hist_series = data.get("nightWeeklyAvgSeries") or []
    if not hist_series:
        return {
            "has_historical": False,
            "hist_peak_vid": None,
            "hist_mean_vid": None,
            "hist_peak_aloft": None,
            "hist_mean_aloft": None,
        }
    vids = [row["vid"] for row in hist_series if row.get("vid") is not None]
    aloft = [row["numAloft"] for row in hist_series if row.get("numAloft") is not None]
    return {
        "has_historical": True,
        "hist_peak_vid": round(max(vids), 3) if vids else None,
        "hist_mean_vid": round(sum(vids) / len(vids), 3) if vids else None,
        "hist_peak_aloft": int(max(aloft)) if aloft else None,
        "hist_mean_aloft": round(sum(aloft) / len(aloft), 1) if aloft else None,
    }


def main() -> int:
    print("=== BIRDCAST MIGRATION DATA ===")
    print("Testing outbreak nights vs quiet nights...")
    print()

    results: dict[str, dict] = {}
    for case in TEST_CASES:
        region = case["region"]
        date_str = case["date"]
        live_url = endpoint(
            f"livemigration/{region}/{date_str}",
            key=API_KEY,
            applyThreshold="true",
        )
        hist_url = endpoint(f"seasonhistorical/{region}/{date_str}", key=API_KEY)
        try:
            live = fetch_json(live_url)
            hist = fetch_json(hist_url)
        except Exception as exc:
            print(f"  {date_str} ({case['label']}): FETCH FAILED: {exc}")
            results[date_str] = {**case, "fetch_error": str(exc)}
            continue

        summary = {}
        summary.update(summarize_live(live))
        summary.update(summarize_hist(hist))
        if summary["has_data"] and summary.get("hist_mean_vid"):
            summary["vid_anomaly_pct"] = round(
                100.0 * (summary["mean_vid"] - summary["hist_mean_vid"]) / summary["hist_mean_vid"],
                1,
            )
        else:
            summary["vid_anomaly_pct"] = None

        results[date_str] = {
            **case,
            **summary,
            "live_raw": live,
            "historical_raw": hist,
        }

        if summary["has_data"]:
            print(
                f"  {date_str} ({case['label']}, {region}): "
                f"peak_vid={summary['peak_vid']} mean_vid={summary['mean_vid']} "
                f"peak_num_aloft={summary['peak_num_aloft']} anomaly={summary['vid_anomaly_pct']}"
            )
        else:
            print(f"  {date_str} ({case['label']}, {region}): NO DATA")

    case_summaries: dict[str, dict] = {}
    for case_name in sorted({row["case"] for row in TEST_CASES}):
        case_rows = [row for row in results.values() if row.get("case") == case_name]
        outbreak = next((row for row in case_rows if "outbreak" in row.get("label", "").lower() or "eve" in row.get("label", "").lower()), None)
        quiets = [row for row in case_rows if "quiet" in row.get("label", "").lower()]
        quiet_mean = None
        quiet_vals = [row["mean_vid"] for row in quiets if row.get("mean_vid") is not None]
        if quiet_vals:
            quiet_mean = round(sum(quiet_vals) / len(quiet_vals), 3)
        anomaly = None
        if outbreak and outbreak.get("mean_vid") is not None and quiet_mean:
            anomaly = round(outbreak["mean_vid"] - quiet_mean, 3)
        case_summaries[case_name] = {
            "outbreak_date": outbreak.get("date") if outbreak else None,
            "outbreak_mean_vid": outbreak.get("mean_vid") if outbreak else None,
            "quiet_mean_vid": quiet_mean,
            "difference_vs_quiet": anomaly,
        }

    payload = {
        "source": "BirdCast dashboard production API discovered from dashboard.birdcast.org",
        "results": results,
        "case_summaries": case_summaries,
    }
    save_json(RESULT_PATH, payload)
    print()
    print(f"Saved to {RESULT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
