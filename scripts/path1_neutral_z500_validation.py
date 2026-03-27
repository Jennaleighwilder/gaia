#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
import random

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
REPORT_PATH = RUNS / "path1_neutral_z500_report.txt"
REPORT_JSON_PATH = RUNS / "path1_neutral_z500_report.json"
Z500_DIR = ROOT / "data" / "cache" / "z500_neutral"
WINDOW = 14
DECAY = 0.20
GULF_ONLY = [
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
Z500_ONLY = [
    "z500_mean_14d",
    "z500_min_14d",
    "z500_anomaly_14d",
    "z500_trend_14d",
    "z500_trough_sig",
    "in_spring",
    "season_score",
]
COMBINED = [
    "gulf_max",
    "gulf_mean",
    "gulf_warm",
    "gulf_trend",
    "z500_mean_14d",
    "z500_min_14d",
    "z500_anomaly_14d",
    "z500_trend_14d",
    "ao_accel",
    "ao_accel_neg",
    "ao_final3_vs_prior",
    "in_spring",
    "season_score",
]


def mean(xs: list[float]) -> float:
    return float(_mean(xs)) if xs else 0.0


def load_z500_cache() -> dict[str, float]:
    out: dict[str, float] = {}
    for path in sorted(Z500_DIR.glob("z500_*.json")):
        with path.open() as f:
            raw = json.load(f)
        for key, value in raw.items():
            try:
                out[str(key)] = float(value)
            except (TypeError, ValueError):
                continue
    return out


def build_z500_climo(z500_cache: dict[str, float]) -> dict[int, float]:
    monthly: dict[int, list[float]] = {}
    for ds, value in z500_cache.items():
        month = int(ds.split("-")[1])
        monthly.setdefault(month, []).append(float(value))
    return {month: mean(values) for month, values in monthly.items()}


def get_all_features(
    center_date: datetime,
    ao_archive: dict[str, float],
    gulf_data: dict[str, dict[str, float | bool | str]],
    z500_cache: dict[str, float],
    z500_climo: dict[int, float],
) -> dict[str, float | int] | None:
    ao_vals: list[float] = []
    weights: list[float] = []
    import math

    for days_back in range(1, WINDOW + 1):
        ds = (center_date - timedelta(days=days_back)).strftime("%Y-%m-%d")
        if ds in ao_archive:
            ao_vals.append(float(ao_archive[ds]))
            weights.append(math.exp(-DECAY * (days_back - 1)))
    if len(ao_vals) < WINDOW // 2:
        return None

    weight_sum = sum(weights)
    w = [value / weight_sum for value in weights]
    features: dict[str, float | int] = {
        "ao_wmean": float(sum(w[i] * ao_vals[i] for i in range(len(ao_vals)))),
        "ao_wmin": float(min(ao_vals[: min(7, len(ao_vals))])),
        "ao_max_plunge": float(
            max((ao_vals[i + 7] - ao_vals[i] for i in range(len(ao_vals) - 7)), default=0.0)
        ),
    }
    if len(ao_vals) >= 14:
        very_recent = mean_window(ao_vals[:3])
        recent = mean_window(ao_vals[3:8])
        prior = mean_window(ao_vals[8:14])
        features["ao_wtrend"] = float(mean_window(ao_vals[:7]) - mean_window(ao_vals[7:14]))
        features["ao_accel"] = float((very_recent - recent) - (recent - prior))
        features["ao_accel_neg"] = int(float(features["ao_accel"]) < -0.1)
        features["ao_final3_vs_prior"] = float(mean_window(ao_vals[:3]) - mean_window(ao_vals[3:]))
    else:
        mid = max(1, len(ao_vals) // 2)
        features["ao_wtrend"] = float(mean_window(ao_vals[:mid]) - mean_window(ao_vals[mid:]))
        features["ao_accel"] = float(mean_window(ao_vals[:mid]) - mean_window(ao_vals[mid:]))
        features["ao_accel_neg"] = int(float(features["ao_accel"]) < -0.1)
        features["ao_final3_vs_prior"] = 0.0

    gulf_vals: list[float] = []
    for weeks_back in range(1, 5):
        check = center_date - timedelta(weeks=weeks_back)
        key = f"{check.year}-W{check.strftime('%W')}"
        if key in gulf_data:
            gulf_vals.append(float(gulf_data[key].get("anomaly", 0.0)))
    features["gulf_max"] = float(max(gulf_vals)) if gulf_vals else 0.0
    features["gulf_mean"] = float(mean(gulf_vals)) if gulf_vals else 0.0
    features["gulf_warm"] = int(float(features["gulf_max"]) > 0.5)
    features["gulf_trend"] = float(gulf_vals[0] - gulf_vals[-1]) if len(gulf_vals) >= 2 else 0.0

    z_vals: list[float] = []
    for days_back in range(1, WINDOW + 1):
        ds = (center_date - timedelta(days=days_back)).strftime("%Y-%m-%d")
        if ds in z500_cache:
            z_vals.append(float(z500_cache[ds]))
    if z_vals:
        climo = float(z500_climo.get(center_date.month, mean(list(z500_climo.values())) if z500_climo else 0.0))
        features["z500_mean_14d"] = float(mean(z_vals))
        features["z500_min_14d"] = float(min(z_vals))
        features["z500_anomaly_14d"] = float(mean(z_vals) - climo)
        features["z500_trend_14d"] = float(mean_window(z_vals[:7]) - mean_window(z_vals[7:14])) if len(z_vals) >= 14 else 0.0
        features["z500_trough_sig"] = int(float(features["z500_anomaly_14d"]) < -20.0)
        features["z500_depth_score"] = float(
            (-float(features["z500_anomaly_14d"]) / 20.0)
            + (-float(features["z500_trend_14d"]) / 10.0)
            + (float(features["gulf_max"]) / 0.5 if float(features["gulf_max"]) > 0 else 0.0)
        )
    else:
        features["z500_mean_14d"] = 0.0
        features["z500_min_14d"] = 0.0
        features["z500_anomaly_14d"] = 0.0
        features["z500_trend_14d"] = 0.0
        features["z500_trough_sig"] = 0
        features["z500_depth_score"] = 0.0

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


def build_neutral_records(
    outbreaks: list[dict],
    oni_lookup: dict[tuple[int, int], float],
    ao_archive: dict[str, float],
    gulf_data: dict[str, dict[str, float | bool | str]],
    z500_cache: dict[str, float],
    z500_climo: dict[int, float],
) -> list[dict]:
    records: list[dict] = []
    outbreak_years = {datetime.strptime(row["date"], "%Y-%m-%d").year for row in outbreaks}
    rng = random.Random(42)

    for outbreak in outbreaks:
        odate = datetime.strptime(outbreak["date"], "%Y-%m-%d")
        phase, _ = get_enso_phase(oni_lookup, odate.year, odate.month)
        if phase != "NEUTRAL":
            continue
        feat = get_all_features(odate, ao_archive, gulf_data, z500_cache, z500_climo)
        if feat is None:
            continue
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
            cf = get_all_features(cdate, ao_archive, gulf_data, z500_cache, z500_climo)
            if cf is None:
                continue
            cf["label"] = 0
            cf["date"] = cdate.strftime("%Y-%m-%d")
            cf["name"] = "CONTROL"
            records.append(cf)
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


def evaluate_records(records: list[dict], feature_cols: list[str]) -> tuple[list[float], float, float]:
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


def fit_full_model(records: list[dict], feature_cols: list[str]) -> list[tuple[str, float]]:
    X_raw = [[float(row.get(col, 0.0)) for col in feature_cols] for row in records]
    y = [int(row["label"]) for row in records]
    means, stds = _scale_fit(X_raw)
    X_scaled = _scale_apply(X_raw, means, stds)
    weights = _fit_logistic(_add_bias(X_scaled), y, seed=42)
    pairs = list(zip(feature_cols, weights[:-1]))
    pairs.sort(key=lambda item: abs(item[1]), reverse=True)
    return pairs


def main() -> int:
    RUNS.mkdir(exist_ok=True)
    buf = StringIO()

    def pr(line: str = "") -> None:
        print(line)
        buf.write(line + "\n")
        REPORT_PATH.write_text(buf.getvalue())

    ao_archive = load_ao_archive()
    outbreaks = load_outbreaks()
    oni_lookup = load_oni_monthly()
    gulf_data = WeeklyOISSTArchive(use_network=False).fetch_gulf_weekly_archive(start_year=1990, end_year=2025)
    z500_cache = load_z500_cache()
    z500_climo = build_z500_climo(z500_cache)

    pr(f"Z500 days cached: {len(z500_cache)}")
    pr(f"Z500 climatology months: {sorted(z500_climo)}")

    records = build_neutral_records(outbreaks, oni_lookup, ao_archive, gulf_data, z500_cache, z500_climo)
    n_outbreaks = int(sum(int(row["label"]) for row in records))
    pr()
    pr(f"Neutral records: {len(records)} ({n_outbreaks} outbreaks)")
    pr()
    pr("=== NEUTRAL PHASE MODEL COMPARISON ===")
    pr("(Target: >0.65 for operational claim)")
    pr()

    results: dict[str, dict] = {}
    for name, feature_cols in (
        ("Gulf-only (baseline)", GULF_ONLY),
        ("Z500-only (new)", Z500_ONLY),
        ("Gulf + Z500 (combined)", COMBINED),
    ):
        aucs, mean_auc, std_auc = evaluate_records(records, feature_cols)
        status = (
            "PASS"
            if mean_auc >= 0.70
            else "MARGINAL"
            if mean_auc >= 0.60
            else "IMPROVEMENT"
            if mean_auc > 0.478
            else "NO CHANGE"
        )
        pr(f"{name}:")
        pr(f"  AUC: {mean_auc:.3f}  std={std_auc:.3f}  [{status}]")
        pr(f"  Folds: {[round(value, 3) for value in aucs]}")

        z500_rows: list[dict] = []
        if any("z500" in col for col in feature_cols):
            pr("  Z500 separation:")
            for feature in [col for col in feature_cols if "z500" in col]:
                outbreak_vals = [float(row.get(feature, 0.0)) for row in records if row["label"] == 1]
                control_vals = [float(row.get(feature, 0.0)) for row in records if row["label"] == 0]
                ob_mean = mean(outbreak_vals)
                ctrl_mean = mean(control_vals)
                sep = (ob_mean - ctrl_mean) / (float(_pstdev(control_vals)) + 0.001) if control_vals else 0.0
                z500_rows.append(
                    {
                        "feature": feature,
                        "outbreak_mean": ob_mean,
                        "control_mean": ctrl_mean,
                        "sep_sigma": sep,
                    }
                )
                pr(f"    {feature:<28}: ob={ob_mean:.1f} ctrl={ctrl_mean:.1f} sep={sep:+.2f}σ")

        top_weights = fit_full_model(records, feature_cols)[:4]
        pr(f"  Top weights: {[(feature, round(weight, 3)) for feature, weight in top_weights]}")
        pr()
        results[name] = {
            "mean_auc": mean_auc,
            "std_auc": std_auc,
            "folds": aucs,
            "top_weights": {feature: float(weight) for feature, weight in top_weights},
            "z500_separation": z500_rows,
        }

    REPORT_JSON_PATH.write_text(json.dumps(results, indent=2))
    pr("Saved: runs/path1_neutral_z500_report.json")
    REPORT_PATH.write_text(buf.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
