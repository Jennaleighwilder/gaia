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

from runtime.ingest.daily_pna_archive import load_pna_archive
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
REPORT_PATH = RUNS / "path1_neutral_pna_report.txt"
REPORT_JSON_PATH = RUNS / "path1_neutral_pna_report.json"
WINDOW = 14
DECAY = 0.20
BASELINE_AUC = 0.464
RAW_FEATURES = [
    "pna_wmean",
    "pna_wmin",
    "pna_days_neg",
    "pna_neg_sig",
    "pna_trend",
    "pna_gulf_interaction",
    "pna_gulf_sig",
    "gulf_max",
    "gulf_mean",
]
MODELS: dict[str, list[str]] = {
    "Gulf-only (baseline 0.464)": [
        "gulf_max",
        "gulf_mean",
        "gulf_warm",
        "in_spring",
        "season_score",
    ],
    "PNA-only": [
        "pna_wmean",
        "pna_wmin",
        "pna_days_neg",
        "pna_trend",
        "pna_neg_sig",
        "in_spring",
        "season_score",
    ],
    "PNA + Gulf": [
        "pna_wmean",
        "pna_wmin",
        "pna_days_neg",
        "pna_trend",
        "gulf_max",
        "gulf_warm",
        "in_spring",
        "season_score",
    ],
    "PNA x Gulf interaction": [
        "pna_gulf_interaction",
        "pna_gulf_sig",
        "gulf_max",
        "pna_wmin",
        "in_spring",
        "season_score",
    ],
    "Full: PNA + Gulf + AO": [
        "pna_wmean",
        "pna_wmin",
        "pna_days_neg",
        "pna_trend",
        "gulf_max",
        "gulf_mean",
        "gulf_warm",
        "ao_accel",
        "in_spring",
        "season_score",
    ],
}


def mean(xs: list[float]) -> float:
    return float(_mean(xs)) if xs else 0.0


def get_features(
    center_date: datetime,
    ao_archive: dict[str, float],
    pna_archive: dict[str, float],
    gulf_data: dict[str, dict[str, float | bool | str]],
) -> dict[str, float | int]:
    pna_vals: list[float] = []
    weights: list[float] = []
    for days_back in range(1, WINDOW + 1):
        ds = (center_date - timedelta(days=days_back)).strftime("%Y-%m-%d")
        if ds in pna_archive:
            pna_vals.append(float(pna_archive[ds]))
            weights.append(math.exp(-DECAY * (days_back - 1)))

    features: dict[str, float | int] = {}
    if pna_vals:
        weight_sum = sum(weights)
        norm = [value / weight_sum for value in weights]
        features["pna_wmean"] = float(sum(norm[i] * pna_vals[i] for i in range(len(pna_vals))))
        features["pna_wmin"] = float(min(pna_vals))
        features["pna_days_neg"] = int(sum(1 for value in pna_vals if value < -0.5))
        features["pna_neg_sig"] = int(float(features["pna_wmin"]) < -1.0)
        features["pna_trend"] = float(mean_window(pna_vals[:7]) - mean_window(pna_vals[7:])) if len(pna_vals) >= 14 else 0.0
        max_plunge = max((pna_vals[i] - pna_vals[i + 7] for i in range(len(pna_vals) - 7)), default=0.0)
        features["pna_plunge"] = float(-max_plunge)
    else:
        for key in ("pna_wmean", "pna_wmin", "pna_days_neg", "pna_neg_sig", "pna_trend", "pna_plunge"):
            features[key] = 0.0

    gulf_vals: list[float] = []
    for weeks_back in range(1, 5):
        check = center_date - timedelta(weeks=weeks_back)
        key = f"{check.year}-W{check.strftime('%W')}"
        if key in gulf_data:
            gulf_vals.append(float(gulf_data[key].get("anomaly", 0.0)))
    features["gulf_max"] = float(max(gulf_vals)) if gulf_vals else 0.0
    features["gulf_mean"] = float(mean(gulf_vals)) if gulf_vals else 0.0
    features["gulf_warm"] = int(float(features["gulf_max"]) > 0.5)

    ao_vals: list[float] = []
    for days_back in range(1, WINDOW + 1):
        ds = (center_date - timedelta(days=days_back)).strftime("%Y-%m-%d")
        if ds in ao_archive:
            ao_vals.append(float(ao_archive[ds]))
    if len(ao_vals) >= 14:
        very_recent = mean_window(ao_vals[:3])
        recent = mean_window(ao_vals[3:8])
        prior = mean_window(ao_vals[8:14])
        features["ao_accel"] = float((very_recent - recent) - (recent - prior))
    else:
        features["ao_accel"] = 0.0

    features["pna_gulf_interaction"] = abs(min(float(features["pna_wmin"]), 0.0)) * float(features["gulf_max"])
    features["pna_gulf_sig"] = int(float(features["pna_wmin"]) < -0.5 and float(features["gulf_max"]) > 0.5)

    doy = center_date.timetuple().tm_yday
    month = center_date.month
    features["in_spring"] = int(month in (3, 4, 5))
    features["season_score"] = (
        0.9
        if 91 <= doy <= 135
        else 0.7
        if 74 <= doy <= 151
        else 0.6
        if doy >= 319
        else 0.1
    )
    return features


def build_records(
    outbreaks: list[dict],
    oni_lookup: dict[tuple[int, int], float],
    ao_archive: dict[str, float],
    pna_archive: dict[str, float],
    gulf_data: dict[str, dict[str, float | bool | str]],
) -> list[dict]:
    records: list[dict] = []
    outbreak_years = {datetime.strptime(row["date"], "%Y-%m-%d").year for row in outbreaks}
    rng = random.Random(42)

    for outbreak in outbreaks:
        odate = datetime.strptime(outbreak["date"], "%Y-%m-%d")
        phase, _ = get_enso_phase(oni_lookup, odate.year, odate.month)
        if phase != "NEUTRAL":
            continue
        record = get_features(odate, ao_archive, pna_archive, gulf_data)
        record["label"] = 1
        record["date"] = outbreak["date"]
        record["name"] = outbreak["name"]
        records.append(record)

        control_years: list[int] = []
        for year in range(1990, 2026):
            if year in outbreak_years or abs(year - odate.year) < 2:
                continue
            control_phase, _ = get_enso_phase(oni_lookup, year, odate.month)
            if control_phase == "NEUTRAL":
                control_years.append(year)
        rng.shuffle(control_years)

        added = 0
        for control_year in control_years:
            cday = min(odate.day, month_last_day(control_year, odate.month))
            cdate = datetime(control_year, odate.month, cday)
            record = get_features(cdate, ao_archive, pna_archive, gulf_data)
            record["label"] = 0
            record["date"] = cdate.strftime("%Y-%m-%d")
            record["name"] = "CONTROL"
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


def evaluate_model(records: list[dict], feature_cols: list[str]) -> tuple[list[float], float, float, list[tuple[str, float]]]:
    X_raw = [[float(row.get(col, 0.0)) for col in feature_cols] for row in records]
    y = [int(row["label"]) for row in records]
    positives = sum(y)
    negatives = len(y) - positives
    k = min(5, positives, negatives)
    if k < 2:
        return [], 0.0, 0.0, []

    aucs: list[float] = []
    for fold_num, (train_idx, test_idx) in enumerate(stratified_kfold_indices(y, k)):
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

    means, stds = _scale_fit(X_raw)
    X_scaled = _scale_apply(X_raw, means, stds)
    weights = _fit_logistic(_add_bias(X_scaled), y, seed=42)
    top = list(zip(feature_cols, weights[:-1]))
    top.sort(key=lambda item: abs(item[1]), reverse=True)
    return aucs, float(mean(aucs)), float(_pstdev(aucs)) if aucs else 0.0, top[:3]


def main() -> int:
    RUNS.mkdir(exist_ok=True)
    buf = StringIO()

    def pr(line: str = "") -> None:
        print(line)
        buf.write(line + "\n")
        REPORT_PATH.write_text(buf.getvalue())

    ao_archive = load_ao_archive()
    pna_archive = load_pna_archive(fetch_if_missing=True)
    gulf_data = WeeklyOISSTArchive(use_network=False).fetch_gulf_weekly_archive(start_year=1990, end_year=2025)
    outbreaks = load_outbreaks()
    oni_lookup = load_oni_monthly()
    records = build_records(outbreaks, oni_lookup, ao_archive, pna_archive, gulf_data)
    n_outbreaks = int(sum(int(row["label"]) for row in records))

    pr(f"Neutral records: {len(records)} ({n_outbreaks} outbreaks)")
    pr()
    pr("=== RAW PNA SEPARATION ===")
    raw_rows: list[dict] = []
    outbreak_rows = [row for row in records if row["label"] == 1]
    control_rows = [row for row in records if row["label"] == 0]
    best_sep_feature = ""
    best_sep_value = -1.0
    for feature in RAW_FEATURES:
        ob_vals = [float(row.get(feature, 0.0)) for row in outbreak_rows]
        ctrl_vals = [float(row.get(feature, 0.0)) for row in control_rows]
        sep = (mean(ob_vals) - mean(ctrl_vals)) / (float(_pstdev(ctrl_vals)) + 0.001) if ctrl_vals else 0.0
        row = {
            "feature": feature,
            "outbreak_mean": mean(ob_vals),
            "control_mean": mean(ctrl_vals),
            "sep_sigma": sep,
        }
        raw_rows.append(row)
        if abs(sep) > best_sep_value:
            best_sep_value = abs(sep)
            best_sep_feature = feature
        pr(f"  {feature:<30}: ob={row['outbreak_mean']:.3f}  ctrl={row['control_mean']:.3f}  sep={sep:+.2f}σ")

    pr()
    pr("=== MODEL COMPARISON ===")
    pr()
    best_model_name = ""
    best_auc = -1.0
    results: dict[str, dict] = {}
    for name, feature_cols in MODELS.items():
        aucs, mean_auc, std_auc, top = evaluate_model(records, feature_cols)
        if mean_auc > best_auc:
            best_auc = mean_auc
            best_model_name = name
        status = (
            "PASS"
            if mean_auc >= 0.70
            else "MARGINAL"
            if mean_auc >= 0.60
            else "IMPROVEMENT"
            if mean_auc > BASELINE_AUC
            else "NO CHANGE"
        )
        flag = " *** BEST" if name == best_model_name and mean_auc == best_auc else ""
        pr(f"{name}:")
        pr(f"  AUC: {mean_auc:.3f}  std={std_auc:.3f}  [{status}]{flag}")
        pr(f"  Folds: {[round(value, 3) for value in aucs]}")
        pr(f"  Top weights: {[(feature, round(weight, 3)) for feature, weight in top]}")
        pr()
        results[name] = {
            "mean_auc": mean_auc,
            "std_auc": std_auc,
            "folds": aucs,
            "top_weights": {feature: float(weight) for feature, weight in top},
        }

    REPORT_JSON_PATH.write_text(
        json.dumps(
            {
                "pna_archive_values": len(pna_archive),
                "raw_separation": raw_rows,
                "best_separation_feature": best_sep_feature,
                "models": results,
                "best_model": best_model_name,
                "best_auc": best_auc,
            },
            indent=2,
        )
    )
    pr("Saved: runs/path1_neutral_pna_report.json")
    pr()
    if best_auc >= 0.65:
        pr(f"RESULT: PNA VALIDATED for neutral phase. AUC={best_auc:.3f}")
        pr("GAIA phase-conditional model:")
        pr("  La Nina: AO plunge (AUC ~0.70)")
        pr("  Neutral: Negative PNA + Gulf SST (AUC validated)")
    elif best_auc > BASELINE_AUC:
        pr(f"RESULT: IMPROVEMENT. PNA adds signal. AUC={best_auc:.3f}")
        pr("Keep PNA. Add more variables.")
    else:
        pr(f"RESULT: PNA did not help. AUC={best_auc:.3f}")
        pr("Neutral phase mechanism still unresolved.")
    REPORT_PATH.write_text(buf.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
