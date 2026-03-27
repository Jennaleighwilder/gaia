#!/usr/bin/env python3
from __future__ import annotations

import json
import random
import sys
import urllib.request
from datetime import datetime
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.ingest.weekly_oisst_archive import WeeklyOISSTArchive
from scripts.path1_daily_window_validation import (
    FEATURE_COLS,
    get_gulf_features_window,
    get_season_features,
    get_weighted_ao_features,
    load_ao_archive,
    load_outbreaks,
)
from scripts.path1_validation import (
    _add_bias,
    _fit_logistic,
    _mean,
    _predict_proba,
    _pstdev,
    _roc_auc,
    _scale_apply,
    _scale_fit,
)

RUNS = ROOT / "runs"
REPORT_PATH = RUNS / "path1_allphase_report.txt"
REPORT_JSON_PATH = RUNS / "path1_allphase_report.json"
ONI_DIR = ROOT / "data" / "global_indices"
ONI_PATH = ONI_DIR / "oni_monthly.dat"
ONI_URL = "https://ftp.cpc.ncep.noaa.gov/htdocs/data/indices/oni.ascii.txt"
WINDOW_DAYS = 14
DECAY = 0.20
BASELINE_AUC = 0.755
PHASES = ["LA_NINA", "EL_NINO", "NEUTRAL"]
SEASON_TO_MONTH = {
    "DJF": 1,
    "JFM": 2,
    "FMA": 3,
    "MAM": 4,
    "AMJ": 5,
    "MJJ": 6,
    "JJA": 7,
    "JAS": 8,
    "ASO": 9,
    "SON": 10,
    "OND": 11,
    "NDJ": 12,
}


def fetch_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_oni_seasonal(text: str) -> dict[tuple[int, int], float]:
    out: dict[tuple[int, int], float] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        season = parts[0].upper()
        if season not in SEASON_TO_MONTH:
            continue
        try:
            year = int(parts[1])
            anomaly = float(parts[3])
        except ValueError:
            continue
        out[(year, SEASON_TO_MONTH[season])] = anomaly
    return out


def load_oni_monthly() -> dict[tuple[int, int], float]:
    if ONI_PATH.exists():
        out: dict[tuple[int, int], float] = {}
        with ONI_PATH.open() as f:
            for line in f:
                parts = line.split()
                if len(parts) < 3:
                    continue
                try:
                    year = int(parts[0])
                    month = int(parts[1])
                    value = float(parts[2])
                except ValueError:
                    continue
                out[(year, month)] = value
        if out:
            return out

    ONI_DIR.mkdir(parents=True, exist_ok=True)
    text = fetch_text(ONI_URL)
    out = parse_oni_seasonal(text)
    with ONI_PATH.open("w") as f:
        for year, month in sorted(out):
            f.write(f"{year} {month} {out[(year, month)]:.2f}\n")
    return out


def get_enso_phase(oni_lookup: dict[tuple[int, int], float], year: int, month: int) -> tuple[str, float]:
    oni = float(oni_lookup.get((year, month), 0.0))
    if oni < -0.5:
        return "LA_NINA", oni
    if oni > 0.5:
        return "EL_NINO", oni
    return "NEUTRAL", oni


def month_last_day(year: int, month: int) -> int:
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    return (next_month - datetime.resolution).day


def build_outbreak_records(
    outbreaks: list[dict],
    ao_archive: dict[str, float],
    gulf_client: WeeklyOISSTArchive,
    oni_lookup: dict[tuple[int, int], float],
) -> list[dict]:
    records: list[dict] = []
    for outbreak in outbreaks:
        odate = datetime.strptime(outbreak["date"], "%Y-%m-%d")
        ao_feat = get_weighted_ao_features(odate, ao_archive, WINDOW_DAYS, DECAY)
        if ao_feat is None:
            continue
        phase, oni = get_enso_phase(oni_lookup, odate.year, odate.month)
        record = {
            "label": 1,
            "phase": phase,
            "oni": oni,
            "name": outbreak["name"],
            "date": outbreak["date"],
        }
        record.update(ao_feat)
        record.update(get_gulf_features_window(odate, gulf_client))
        record.update(get_season_features(odate))
        records.append(record)
    return records


def build_control_records(
    outbreaks: list[dict],
    ao_archive: dict[str, float],
    gulf_client: WeeklyOISSTArchive,
    oni_lookup: dict[tuple[int, int], float],
) -> list[dict]:
    outbreak_years = {datetime.strptime(row["date"], "%Y-%m-%d").year for row in outbreaks}
    min_year = min(outbreak_years)
    max_year = max(outbreak_years)
    quiet_years = [year for year in range(min_year, max_year + 1) if year not in outbreak_years]
    rng = random.Random(42)
    records: list[dict] = []

    for outbreak in outbreaks:
        odate = datetime.strptime(outbreak["date"], "%Y-%m-%d")
        candidate_years = [year for year in quiet_years if abs(year - odate.year) >= 2]
        rng.shuffle(candidate_years)
        added = 0
        for control_year in candidate_years:
            day = min(odate.day, month_last_day(control_year, odate.month))
            control_date = datetime(control_year, odate.month, day)
            ao_feat = get_weighted_ao_features(control_date, ao_archive, WINDOW_DAYS, DECAY)
            if ao_feat is None:
                continue
            phase, oni = get_enso_phase(oni_lookup, control_year, odate.month)
            record = {
                "label": 0,
                "phase": phase,
                "oni": oni,
                "name": "CONTROL",
                "date": control_date.strftime("%Y-%m-%d"),
                "matched_to": outbreak["name"],
            }
            record.update(ao_feat)
            record.update(get_gulf_features_window(control_date, gulf_client))
            record.update(get_season_features(control_date))
            records.append(record)
            added += 1
            if added >= 5:
                break
    return records


def stratified_kfold_indices(y: list[int], k: int, seed: int = 42) -> list[tuple[list[int], list[int]]]:
    pos_idx = [idx for idx, label in enumerate(y) if label == 1]
    neg_idx = [idx for idx, label in enumerate(y) if label == 0]
    rng = random.Random(seed)
    rng.shuffle(pos_idx)
    rng.shuffle(neg_idx)
    pos_folds = [[] for _ in range(k)]
    neg_folds = [[] for _ in range(k)]
    for i, idx in enumerate(pos_idx):
        pos_folds[i % k].append(idx)
    for i, idx in enumerate(neg_idx):
        neg_folds[i % k].append(idx)

    all_idx = set(range(len(y)))
    folds: list[tuple[list[int], list[int]]] = []
    for fold_num in range(k):
        test = sorted(pos_folds[fold_num] + neg_folds[fold_num])
        train = sorted(all_idx - set(test))
        folds.append((train, test))
    return folds


def evaluate_records(records: list[dict]) -> dict | None:
    if not records:
        return None
    X_raw = [[float(row.get(col, 0.0)) for col in FEATURE_COLS] for row in records]
    y = [int(row["label"]) for row in records]
    positives = sum(y)
    negatives = len(y) - positives
    k = min(5, positives, negatives)
    if k < 2:
        return None

    aucs: list[float] = []
    for fold_num, (train_idx, test_idx) in enumerate(stratified_kfold_indices(y, k=k, seed=42)):
        y_train = [y[i] for i in train_idx]
        y_test = [y[i] for i in test_idx]
        if sum(y_train) == 0 or sum(y_test) == 0 or sum(1 for v in y_test if v == 0) == 0:
            continue
        X_train = [X_raw[i] for i in train_idx]
        X_test = [X_raw[i] for i in test_idx]
        means, stds = _scale_fit(X_train)
        X_train_s = _scale_apply(X_train, means, stds)
        X_test_s = _scale_apply(X_test, means, stds)
        X_train_b = _add_bias(X_train_s)
        X_test_b = _add_bias(X_test_s)
        weights = _fit_logistic(X_train_b, y_train, seed=42 + fold_num)
        probs = _predict_proba(X_test_b, weights)
        aucs.append(_roc_auc(y_test, probs))

    if not aucs:
        return None
    return {
        "fold_aucs": [float(v) for v in aucs],
        "mean_auc": float(_mean(aucs)),
        "std_auc": float(_pstdev(aucs)),
        "variance_auc": float(_pstdev(aucs) ** 2),
        "n_records": len(records),
        "n_outbreaks": positives,
        "n_controls": negatives,
        "k_folds": len(aucs),
    }


def fit_full_model(records: list[dict]) -> list[tuple[str, float]]:
    X_raw = [[float(row.get(col, 0.0)) for col in FEATURE_COLS] for row in records]
    y = [int(row["label"]) for row in records]
    means, stds = _scale_fit(X_raw)
    X_scaled = _scale_apply(X_raw, means, stds)
    X_bias = _add_bias(X_scaled)
    weights = _fit_logistic(X_bias, y, seed=42)
    feature_weights = list(zip(FEATURE_COLS, weights[:-1]))
    feature_weights.sort(key=lambda item: abs(item[1]), reverse=True)
    return feature_weights


def main() -> int:
    RUNS.mkdir(exist_ok=True)
    buf = StringIO()

    def pr(line: str = "") -> None:
        print(line)
        buf.write(line + "\n")

    ao_archive = load_ao_archive()
    outbreaks = load_outbreaks()
    oni_lookup = load_oni_monthly()
    gulf_client = WeeklyOISSTArchive(use_network=False)

    pr("=== PATH 1 ALL-PHASE VALIDATION ===")
    pr(f"Fixed params from weighted search: window={WINDOW_DAYS} decay={DECAY:.2f}")
    pr(f"Legacy La Nina benchmark: {BASELINE_AUC:.3f}")
    pr("Gulf weekly source: cached archive with zero fallback for uncached weeks")
    pr()
    pr(f"Total outbreaks in database: {len(outbreaks)}")

    outbreak_records = build_outbreak_records(outbreaks, ao_archive, gulf_client, oni_lookup)
    control_records = build_control_records(outbreaks, ao_archive, gulf_client, oni_lookup)
    all_records = outbreak_records + control_records

    pr(f"Outbreak windows with AO data: {len(outbreak_records)}")
    pr(f"Control windows: {len(control_records)}")
    pr(f"Total records: {len(all_records)}")
    pr()

    phase_counts = {phase: 0 for phase in PHASES}
    for row in outbreak_records:
        phase_counts[row["phase"]] = phase_counts.get(row["phase"], 0) + 1
    pr("Outbreak phase counts:")
    for phase in PHASES:
        pr(f"  {phase:<8}: {phase_counts.get(phase, 0)}")

    results: dict[str, dict | None] = {}
    phase_views: dict[str, dict[str, dict | None]] = {}
    all_result = evaluate_records(all_records)
    results["ALL_PHASES"] = all_result

    pr()
    pr("=== ALL PHASES ===")
    if all_result is None:
        pr("Insufficient data for all-phase validation.")
    else:
        pr(f"Folds: {[round(v, 3) for v in all_result['fold_aucs']]}")
        pr(f"Mean AUC: {all_result['mean_auc']:.3f}  std={all_result['std_auc']:.3f}")

    for phase in PHASES:
        phase_records = [row for row in all_records if row["phase"] == phase]
        phase_result = evaluate_records(phase_records)
        matched_outbreaks = [row for row in outbreak_records if row["phase"] == phase]
        matched_names = {row["name"] for row in matched_outbreaks}
        matched_controls = [row for row in control_records if row.get("matched_to") in matched_names]
        matched_result = evaluate_records(matched_outbreaks + matched_controls)
        results[phase] = phase_result
        phase_views[phase] = {
            "same_phase_controls": phase_result,
            "matched_seasonal_controls": matched_result,
        }
        pr()
        pr(f"=== {phase} ===")
        if matched_result is not None:
            pr(
                f"Matched seasonal controls: n_outbreaks={matched_result['n_outbreaks']} "
                f"n_controls={matched_result['n_controls']}"
            )
            pr(f"  Folds: {[round(v, 3) for v in matched_result['fold_aucs']]}")
            pr(
                f"  Mean AUC: {matched_result['mean_auc']:.3f}  "
                f"std={matched_result['std_auc']:.3f}"
            )
            if matched_result["n_outbreaks"] < 3:
                pr("  Caution: fewer than 3 outbreak windows, so this estimate is not stable.")
        else:
            pr("Matched seasonal controls: insufficient outbreaks to validate.")

        if phase_result is None:
            pr("Insufficient outbreaks to validate.")
            continue
        pr("Same-phase controls:")
        pr(f"n_outbreaks={phase_result['n_outbreaks']} n_controls={phase_result['n_controls']}")
        pr(f"Folds: {[round(v, 3) for v in phase_result['fold_aucs']]}")
        pr(f"Mean AUC: {phase_result['mean_auc']:.3f}  std={phase_result['std_auc']:.3f}")
        if phase_result["n_outbreaks"] < 3:
            pr("Caution: fewer than 3 outbreak windows, so this phase estimate is not stable.")

    importances = fit_full_model(all_records)
    top_features = importances[:6]
    pr()
    pr("Top features (all phases):")
    for feature_name, weight in top_features:
        pr(f"  {feature_name:<20}: {weight:+.3f}")

    all_mean_auc = float(all_result["mean_auc"]) if all_result else 0.0
    delta_vs_baseline = all_mean_auc - BASELINE_AUC
    variance_dropped = bool(all_result and all_result["std_auc"] < 0.15)

    payload = {
        "window_days": WINDOW_DAYS,
        "decay": DECAY,
        "legacy_lanina_baseline_auc": BASELINE_AUC,
        "all_phases_beats_baseline": all_mean_auc > BASELINE_AUC,
        "delta_vs_lanina_baseline": float(delta_vs_baseline),
        "variance_dropped_meaningfully": variance_dropped,
        "oni_source": ONI_URL,
        "n_outbreak_windows": len(outbreak_records),
        "n_control_windows": len(control_records),
        "phase_counts": phase_counts,
        "results": results,
        "phase_views": phase_views,
        "top_features_all_phases": {name: float(weight) for name, weight in top_features},
    }

    REPORT_JSON_PATH.write_text(json.dumps(payload, indent=2))
    REPORT_PATH.write_text(buf.getvalue())
    pr()
    pr(f"Saved to {REPORT_JSON_PATH.relative_to(ROOT)}")
    REPORT_PATH.write_text(buf.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
