#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import random
import sys
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.ingest.weekly_oisst_archive import WeeklyOISSTArchive
from scripts.path1_allphase_validation import get_enso_phase, load_oni_monthly, month_last_day
from scripts.path1_daily_window_validation import load_ao_archive, load_outbreaks, mean_window
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
REPORT_PATH = RUNS / "path1_phase_conditional_report.txt"
REPORT_JSON_PATH = RUNS / "path1_phase_conditional_report.json"
WINDOW = 14
DECAY = 0.20
LA_NINA_FEATURES = [
    "ao_wmin",
    "ao_max_plunge",
    "ao_accel",
    "ao_accel_neg",
    "ao_final3_vs_prior",
    "ao_wtrend",
    "gulf_max",
    "in_spring",
    "season_score",
]
NEUTRAL_FEATURES = [
    "gulf_max",
    "gulf_mean",
    "gulf_warm",
    "gulf_trend",
    "ao_accel",
    "ao_accel_neg",
    "ao_final3_vs_prior",
    "in_spring",
    "season_score",
]


def mean(xs: list[float]) -> float:
    return float(_mean(xs)) if xs else 0.0


def get_ao_features(center_date: datetime, ao_archive: dict[str, float]) -> dict[str, float | int] | None:
    ao_vals: list[float] = []
    weights: list[float] = []
    for d in range(1, WINDOW + 1):
        ds = (center_date - timedelta(days=d)).strftime("%Y-%m-%d")
        if ds in ao_archive:
            ao_vals.append(float(ao_archive[ds]))
            weights.append(math.exp(-DECAY * (d - 1)))
    if len(ao_vals) < WINDOW // 2:
        return None

    weight_sum = sum(weights)
    w = [value / weight_sum for value in weights]
    recent_n = min(7, len(ao_vals))
    features: dict[str, float | int] = {
        "ao_wmean": float(sum(w[i] * ao_vals[i] for i in range(len(ao_vals)))),
        "ao_wmin": float(min(ao_vals[:recent_n])),
    }
    if len(ao_vals) >= 14:
        features["ao_wtrend"] = float(mean_window(ao_vals[:7]) - mean_window(ao_vals[7:14]))
        very_recent = mean_window(ao_vals[:3])
        recent = mean_window(ao_vals[3:8])
        prior = mean_window(ao_vals[8:14])
        features["ao_accel"] = float((very_recent - recent) - (recent - prior))
        features["ao_accel_neg"] = int(float(features["ao_accel"]) < -0.1)
        features["ao_final3_vs_prior"] = float(mean_window(ao_vals[:3]) - mean_window(ao_vals[3:]))
    else:
        mid = max(1, len(ao_vals) // 2)
        features["ao_wtrend"] = float(mean_window(ao_vals[:mid]) - mean_window(ao_vals[mid:]))
        features["ao_accel"] = float(mean_window(ao_vals[:mid]) - mean_window(ao_vals[mid:]))
        features["ao_accel_neg"] = int(float(features["ao_accel"]) < -0.1)
        features["ao_final3_vs_prior"] = 0.0

    max_plunge = 0.0
    if len(ao_vals) >= 8:
        for i in range(len(ao_vals) - 7):
            plunge = ao_vals[i + 7] - ao_vals[i]
            if plunge > max_plunge:
                max_plunge = plunge
    features["ao_max_plunge"] = float(max_plunge)
    features["ao_plunge_sig"] = int(max_plunge > 1.0)
    return features


def get_gulf_features(center_date: datetime, gulf_data: dict[str, dict[str, float | bool | str]], weeks: int = 5) -> dict[str, float | int]:
    anom_vals: list[float] = []
    for weeks_back in range(1, weeks + 1):
        check = center_date - timedelta(weeks=weeks_back)
        key = f"{check.year}-W{check.strftime('%W')}"
        if key in gulf_data:
            anom_vals.append(float(gulf_data[key].get("anomaly", 0.0)))
    if not anom_vals:
        return {"gulf_max": 0.0, "gulf_mean": 0.0, "gulf_warm": 0, "gulf_trend": 0.0}
    return {
        "gulf_max": float(max(anom_vals)),
        "gulf_mean": float(mean(anom_vals)),
        "gulf_warm": int(max(anom_vals) > 0.5),
        "gulf_trend": float(anom_vals[0] - anom_vals[-1]) if len(anom_vals) >= 2 else 0.0,
    }


def get_season_features(date: datetime) -> dict[str, float | int]:
    doy = date.timetuple().tm_yday
    month = date.month
    return {
        "in_spring": int(month in (3, 4, 5)),
        "in_peak": int(91 <= doy <= 135),
        "season_score": (
            0.9
            if 91 <= doy <= 135
            else 0.7
            if 74 <= doy <= 151
            else 0.6
            if doy >= 319
            else 0.1
        ),
    }


def build_phase_records(
    target_phase: str,
    feature_cols: list[str],
    ao_archive: dict[str, float],
    gulf_data: dict[str, dict[str, float | bool | str]],
    outbreaks: list[dict],
    oni_lookup: dict[tuple[int, int], float],
) -> list[dict]:
    records: list[dict] = []
    outbreak_years = {datetime.strptime(row["date"], "%Y-%m-%d").year for row in outbreaks}
    rng = random.Random(42)

    for outbreak in outbreaks:
        odate = datetime.strptime(outbreak["date"], "%Y-%m-%d")
        phase, _ = get_enso_phase(oni_lookup, odate.year, odate.month)
        if phase != target_phase:
            continue
        ao_features = get_ao_features(odate, ao_archive)
        if ao_features is None:
            continue
        record = {"label": 1, "date": outbreak["date"], "name": outbreak["name"]}
        record.update(ao_features)
        record.update(get_gulf_features(odate, gulf_data))
        record.update(get_season_features(odate))
        records.append(record)

    for outbreak in outbreaks:
        odate = datetime.strptime(outbreak["date"], "%Y-%m-%d")
        phase, _ = get_enso_phase(oni_lookup, odate.year, odate.month)
        if phase != target_phase:
            continue
        control_years = []
        for year in range(1990, 2026):
            if year in outbreak_years or abs(year - odate.year) < 2:
                continue
            control_phase, _ = get_enso_phase(oni_lookup, year, odate.month)
            if control_phase == target_phase:
                control_years.append(year)
        rng.shuffle(control_years)

        added = 0
        for control_year in control_years:
            cday = min(odate.day, month_last_day(control_year, odate.month))
            cdate = datetime(control_year, odate.month, cday)
            ao_features = get_ao_features(cdate, ao_archive)
            if ao_features is None:
                continue
            record = {"label": 0, "date": cdate.strftime("%Y-%m-%d"), "name": "CONTROL"}
            record.update(ao_features)
            record.update(get_gulf_features(cdate, gulf_data))
            record.update(get_season_features(cdate))
            records.append(record)
            added += 1
            if added >= 5:
                break

    # Keep the payload focused on the requested feature set.
    trimmed: list[dict] = []
    for row in records:
        trimmed_row = {key: row.get(key, 0.0) for key in feature_cols}
        trimmed_row["label"] = row["label"]
        trimmed_row["date"] = row["date"]
        trimmed_row["name"] = row["name"]
        trimmed.append(trimmed_row)
    return trimmed


def stratified_kfold_indices(y: list[int], k: int, seed: int = 42) -> list[tuple[list[int], list[int]]]:
    pos_idx = [idx for idx, label in enumerate(y) if label == 1]
    neg_idx = [idx for idx, label in enumerate(y) if label == 0]
    rng = random.Random(seed)
    rng.shuffle(pos_idx)
    rng.shuffle(neg_idx)
    pos_folds = [[] for _ in range(k)]
    neg_folds = [[] for _ in range(k)]
    for idx, pos in enumerate(pos_idx):
        pos_folds[idx % k].append(pos)
    for idx, neg in enumerate(neg_idx):
        neg_folds[idx % k].append(neg)
    all_idx = set(range(len(y)))
    folds: list[tuple[list[int], list[int]]] = []
    for fold_num in range(k):
        test = sorted(pos_folds[fold_num] + neg_folds[fold_num])
        train = sorted(all_idx - set(test))
        folds.append((train, test))
    return folds


def evaluate_records(records: list[dict], feature_cols: list[str]) -> tuple[list[float], float, float]:
    X_raw = [[float(row.get(col, 0.0)) for col in feature_cols] for row in records]
    y = [int(row["label"]) for row in records]
    positives = sum(y)
    negatives = len(y) - positives
    k = min(5, positives, negatives)
    if k < 2:
        return [], 0.0, 0.0
    aucs: list[float] = []
    for fold_num, (train_idx, test_idx) in enumerate(stratified_kfold_indices(y, k, seed=42)):
        y_train = [y[i] for i in train_idx]
        y_test = [y[i] for i in test_idx]
        if sum(y_train) == 0 or sum(y_test) == 0 or sum(1 for value in y_test if value == 0) == 0:
            continue
        X_train = [X_raw[i] for i in train_idx]
        X_test = [X_raw[i] for i in test_idx]
        means, stds = _scale_fit(X_train)
        X_train_s = _scale_apply(X_train, means, stds)
        X_test_s = _scale_apply(X_test, means, stds)
        weights = _fit_logistic(_add_bias(X_train_s), y_train, seed=42 + fold_num)
        probs = _predict_proba(_add_bias(X_test_s), weights)
        aucs.append(_roc_auc(y_test, probs))
    return aucs, float(mean(aucs)), float(_pstdev(aucs)) if aucs else 0.0


def fit_full_model(records: list[dict], feature_cols: list[str]) -> list[tuple[str, float]]:
    X_raw = [[float(row.get(col, 0.0)) for col in feature_cols] for row in records]
    y = [int(row["label"]) for row in records]
    means, stds = _scale_fit(X_raw)
    X_scaled = _scale_apply(X_raw, means, stds)
    weights = _fit_logistic(_add_bias(X_scaled), y, seed=42)
    feature_weights = list(zip(feature_cols, weights[:-1]))
    feature_weights.sort(key=lambda item: abs(item[1]), reverse=True)
    return feature_weights


def main() -> int:
    RUNS.mkdir(exist_ok=True)
    buf = StringIO()

    def pr(line: str = "") -> None:
        print(line)
        buf.write(line + "\n")

    random.seed(42)
    ao_archive = load_ao_archive()
    outbreaks = load_outbreaks()
    oni_lookup = load_oni_monthly()
    gulf_data = WeeklyOISSTArchive(use_network=False).fetch_gulf_weekly_archive(start_year=1990, end_year=2025)

    pr("=" * 60)
    pr("PATH 1 PHASE-CONDITIONAL MODEL")
    pr("La Nina -> AO-primary  |  Neutral -> Gulf-primary")
    pr("=" * 60)

    results: dict[str, dict] = {}
    for phase, feature_cols in (("LA_NINA", LA_NINA_FEATURES), ("NEUTRAL", NEUTRAL_FEATURES)):
        records = build_phase_records(phase, feature_cols, ao_archive, gulf_data, outbreaks, oni_lookup)
        n_outbreaks = int(sum(row["label"] for row in records))
        n_controls = len(records) - n_outbreaks
        pr()
        pr(f"{phase}: {n_outbreaks} outbreaks, {n_controls} controls")
        if n_outbreaks < 3:
            pr("  Insufficient outbreaks - skip")
            continue

        aucs, mean_auc, std_auc = evaluate_records(records, feature_cols)
        status = "PASS" if mean_auc >= 0.70 else "MARGINAL" if mean_auc >= 0.60 else "FAIL"
        pr(f"  AUC:    {mean_auc:.3f}  std={std_auc:.3f}  [{status}]")
        pr(f"  Folds:  {[round(value, 3) for value in aucs]}")
        pr("  Feature separation:")

        feature_separation: list[dict] = []
        for feature in feature_cols:
            outbreak_vals = [float(row.get(feature, 0.0)) for row in records if row["label"] == 1]
            control_vals = [float(row.get(feature, 0.0)) for row in records if row["label"] == 0]
            ob_mean = mean(outbreak_vals)
            ctrl_mean = mean(control_vals)
            sep = (ob_mean - ctrl_mean) / (float(_pstdev(control_vals)) + 0.001) if control_vals else 0.0
            row = {
                "feature": feature,
                "outbreak_mean": ob_mean,
                "control_mean": ctrl_mean,
                "sep_sigma": sep,
            }
            feature_separation.append(row)
            if abs(sep) > 0.2:
                pr(
                    f"    {feature:<28}: ob={ob_mean:.3f} ctrl={ctrl_mean:.3f} sep={sep:+.2f}σ"
                )

        top_weights = fit_full_model(records, feature_cols)[:5]
        pr(f"  Top weights: {[(name, round(weight, 3)) for name, weight in top_weights]}")

        results[phase] = {
            "mean_auc": mean_auc,
            "std_auc": std_auc,
            "fold_aucs": aucs,
            "n_outbreaks": n_outbreaks,
            "n_controls": n_controls,
            "feature_cols": feature_cols,
            "status": status,
            "top_weights": {name: float(weight) for name, weight in top_weights},
            "feature_separation": feature_separation,
        }

    pr()
    pr("=" * 60)
    pr("COMBINED OPERATIONAL ASSESSMENT")
    pr("=" * 60)
    la_nina = results.get("LA_NINA", {})
    neutral = results.get("NEUTRAL", {})
    pr(f"La Nina model:  AUC {la_nina.get('mean_auc', 0.0):.3f}  [{la_nina.get('status', 'N/A')}]")
    pr(f"Neutral model:  AUC {neutral.get('mean_auc', 0.0):.3f}  [{neutral.get('status', 'N/A')}]")
    pr()
    if la_nina.get("mean_auc", 0.0) >= 0.70 and neutral.get("mean_auc", 0.0) >= 0.60:
        pr("RESULT: OPERATIONAL - phase-conditional model covers both major regimes")
        pr("GAIA can issue phase-aware elevated risk assessments")
    elif la_nina.get("mean_auc", 0.0) >= 0.70:
        pr("RESULT: LA NINA VALIDATED - issue warnings during La Nina phases only")
        pr("Neutral phase requires Z500 or additional variables")
    else:
        pr("RESULT: NEEDS MORE WORK - neither phase model at operational threshold")

    REPORT_PATH.write_text(buf.getvalue())
    REPORT_JSON_PATH.write_text(json.dumps(results, indent=2))
    pr()
    pr("Saved: runs/path1_phase_conditional_report.json")
    REPORT_PATH.write_text(buf.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
