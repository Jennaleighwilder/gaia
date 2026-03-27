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
from scripts.path1_allphase_validation import get_enso_phase, load_oni_monthly, month_last_day
from scripts.path1_daily_window_validation import load_ao_archive, load_outbreaks
from scripts.path1_neutral_z500_validation import build_z500_climo, load_z500_cache, mean
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
REPORT_PATH = RUNS / "path1_neutral_interaction_report.txt"
REPORT_JSON_PATH = RUNS / "path1_neutral_interaction_report.json"
WINDOW = 14
BASELINE_AUC = 0.464
RAW_FEATURES = [
    "trough_gulf_interaction",
    "trough_gulf_sig",
    "trough_gulf_ratio",
    "gulf_max",
    "z500_anom",
]
MODELS: dict[str, list[str]] = {
    "Gulf-only (baseline)": ["gulf_max", "gulf_mean", "gulf_warm", "in_spring", "season_score"],
    "Interaction only": ["trough_gulf_interaction", "in_spring", "season_score"],
    "Binary combined": ["trough_gulf_sig", "gulf_max", "in_spring", "season_score"],
    "Interaction + Gulf": [
        "trough_gulf_interaction",
        "gulf_max",
        "gulf_warm",
        "in_spring",
        "season_score",
    ],
    "Full interaction set": [
        "trough_gulf_interaction",
        "trough_gulf_sig",
        "trough_gulf_ratio",
        "gulf_max",
        "z500_anom",
        "in_spring",
        "season_score",
    ],
}


def get_features(
    center_date: datetime,
    ao_archive: dict[str, float],
    gulf_data: dict[str, dict[str, float | bool | str]],
    z500_cache: dict[str, float],
    z500_climo: dict[int, float],
) -> dict[str, float | int]:
    from datetime import timedelta

    gulf_vals: list[float] = []
    for weeks_back in range(1, 5):
        check = center_date - timedelta(weeks=weeks_back)
        key = f"{check.year}-W{check.strftime('%W')}"
        if key in gulf_data:
            gulf_vals.append(float(gulf_data[key].get("anomaly", 0.0)))
    gulf_max = float(max(gulf_vals)) if gulf_vals else 0.0
    gulf_mean = float(mean(gulf_vals)) if gulf_vals else 0.0

    z_vals: list[float] = []
    for days_back in range(1, WINDOW + 1):
        ds = (center_date - timedelta(days=days_back)).strftime("%Y-%m-%d")
        if ds in z500_cache:
            z_vals.append(float(z500_cache[ds]))
    climo = float(z500_climo.get(center_date.month, 5500.0))
    z500_anom = float(mean(z_vals) - climo) if z_vals else 0.0
    z500_min = float(min(z_vals)) if z_vals else 0.0

    ao_vals: list[float] = []
    for days_back in range(1, WINDOW + 1):
        ds = (center_date - timedelta(days=days_back)).strftime("%Y-%m-%d")
        if ds in ao_archive:
            ao_vals.append(float(ao_archive[ds]))
    if not ao_vals:
        ao_vals = [0.0]
    import numpy as np

    ao = np.asarray(ao_vals, dtype=float)

    doy = center_date.timetuple().tm_yday
    month = center_date.month
    in_spring = int(month in (3, 4, 5))
    season_score = (
        0.9
        if 91 <= doy <= 135
        else 0.7
        if 74 <= doy <= 151
        else 0.6
        if doy >= 319
        else 0.1
    )

    trough_gulf_interaction = abs(z500_anom) * gulf_max
    trough_gulf_sig = int(z500_anom < -10.0 and gulf_max > 0.5)
    trough_depth = max(0.0, -z500_anom)
    trough_gulf_ratio = gulf_max * trough_depth / (abs(z500_anom) + 1.0)

    return {
        "gulf_max": gulf_max,
        "gulf_mean": gulf_mean,
        "gulf_warm": int(gulf_max > 0.5),
        "z500_anom": z500_anom,
        "z500_min": z500_min,
        "ao_accel": float((mean(ao[:3].tolist()) - mean(ao[3:8].tolist())) - (mean(ao[3:8].tolist()) - mean(ao[8:14].tolist())))
        if len(ao) >= 14
        else 0.0,
        "trough_gulf_interaction": float(trough_gulf_interaction),
        "trough_gulf_sig": int(trough_gulf_sig),
        "trough_gulf_ratio": float(trough_gulf_ratio),
        "in_spring": in_spring,
        "season_score": float(season_score),
    }


def build_records(
    outbreaks: list[dict],
    oni_lookup: dict[tuple[int, int], float],
    ao_archive: dict[str, float],
    gulf_data: dict[str, dict[str, float | bool | str]],
    z500_cache: dict[str, float],
    z500_climo: dict[int, float],
) -> list[dict]:
    import random

    records: list[dict] = []
    outbreak_years = {datetime.strptime(o["date"], "%Y-%m-%d").year for o in outbreaks}
    rng = random.Random(42)

    for outbreak in outbreaks:
        odate = datetime.strptime(outbreak["date"], "%Y-%m-%d")
        phase, _ = get_enso_phase(oni_lookup, odate.year, odate.month)
        if phase != "NEUTRAL":
            continue
        feat = get_features(odate, ao_archive, gulf_data, z500_cache, z500_climo)
        feat["label"] = 1
        feat["date"] = outbreak["date"]
        feat["name"] = outbreak["name"]
        records.append(feat)

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
            feat = get_features(cdate, ao_archive, gulf_data, z500_cache, z500_climo)
            feat["label"] = 0
            feat["date"] = cdate.strftime("%Y-%m-%d")
            feat["name"] = "CONTROL"
            records.append(feat)
            added += 1
            if added >= 5:
                break
    return records


def stratified_kfold_indices(y: list[int], k: int, seed: int = 42) -> list[tuple[list[int], list[int]]]:
    import random

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


def evaluate_model(records: list[dict], feature_cols: list[str]) -> tuple[list[float], float, float]:
    X_raw = [[float(row.get(col, 0.0)) for col in feature_cols] for row in records]
    y = [int(row["label"]) for row in records]
    positives = sum(y)
    negatives = len(y) - positives
    k = min(5, positives, negatives)
    if k < 2:
        return [], 0.0, 0.0
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
    return aucs, float(mean(aucs)), float(_pstdev(aucs)) if aucs else 0.0


def main() -> int:
    RUNS.mkdir(exist_ok=True)
    buf = StringIO()

    def pr(line: str = "") -> None:
        print(line)
        buf.write(line + "\n")
        REPORT_PATH.write_text(buf.getvalue())

    ao_archive = load_ao_archive()
    gulf_data = WeeklyOISSTArchive(use_network=False).fetch_gulf_weekly_archive(start_year=1990, end_year=2025)
    outbreaks = load_outbreaks()
    z500_cache = load_z500_cache()
    z500_climo = build_z500_climo(z500_cache)
    oni_lookup = load_oni_monthly()
    records = build_records(outbreaks, oni_lookup, ao_archive, gulf_data, z500_cache, z500_climo)
    n_outbreaks = int(sum(int(row["label"]) for row in records))

    pr(f"Neutral records: {len(records)} ({n_outbreaks} outbreaks)")
    pr()
    pr("=== RAW INTERACTION VALUES ===")

    raw_separation: list[dict] = []
    outbreak_rows = [row for row in records if row["label"] == 1]
    control_rows = [row for row in records if row["label"] == 0]
    best_sep_feature = ""
    best_sep_value = -1.0
    for feature in RAW_FEATURES:
        ob_vals = [float(row.get(feature, 0.0)) for row in outbreak_rows]
        ctrl_vals = [float(row.get(feature, 0.0)) for row in control_rows]
        ob_mean = float(mean(ob_vals))
        ctrl_mean = float(mean(ctrl_vals))
        sep = (ob_mean - ctrl_mean) / (float(_pstdev(ctrl_vals)) + 0.001) if ctrl_vals else 0.0
        raw_separation.append(
            {
                "feature": feature,
                "outbreak_mean": ob_mean,
                "control_mean": ctrl_mean,
                "sep_sigma": sep,
            }
        )
        if abs(sep) > best_sep_value:
            best_sep_value = abs(sep)
            best_sep_feature = feature
        pr(f"  {feature:<30}: ob={ob_mean:.3f}  ctrl={ctrl_mean:.3f}  sep={sep:+.2f}σ")

    pr()
    pr("=== MODEL COMPARISON ===")
    pr()
    best_model_name = ""
    best_auc = -1.0
    results: dict[str, dict] = {}
    for name, feature_cols in MODELS.items():
        aucs, mean_auc, std_auc = evaluate_model(records, feature_cols)
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
        pr()
        results[name] = {
            "mean_auc": mean_auc,
            "std_auc": std_auc,
            "folds": aucs,
            "feature_cols": feature_cols,
            "status": status,
        }

    payload = {
        "raw_separation": raw_separation,
        "best_separation_feature": best_sep_feature,
        "models": results,
    }
    REPORT_JSON_PATH.write_text(json.dumps(payload, indent=2))
    pr("Saved: runs/path1_neutral_interaction_report.json")
    REPORT_PATH.write_text(buf.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
