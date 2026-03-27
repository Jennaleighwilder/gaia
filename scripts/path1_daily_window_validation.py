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
from scripts.path1_validation import (
    LA_NINA_PERIODS,
    OUTBREAK_DB,
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
AO_ARCHIVE_PATH = ROOT / "data" / "cache" / "era5_daily_ao" / "daily_ao_archive.json"
REPORT_PATH = RUNS / "path1_window_report.txt"
REPORT_JSON_PATH = RUNS / "path1_window_report.json"
GRID_JSON_PATH = RUNS / "path1_window_gridsearch.json"
BASELINE_AUC = 0.724
WINDOWS = [7, 10, 14, 21, 28]
DECAYS = [0.0, 0.05, 0.10, 0.15, 0.20]
FEATURE_COLS = [
    "ao_wmean",
    "ao_wmin",
    "ao_wtrend",
    "ao_accel",
    "ao_accel_sign",
    "ao_final3_vs_prior",
    "ao_max_plunge",
    "ao_plunge_sig",
    "gulf_max",
    "gulf_warm",
    "in_spring",
    "in_peak",
    "season_score",
]


def date_in_la_nina(date: datetime) -> bool:
    for sy, sm, ey, em in LA_NINA_PERIODS:
        start = datetime(sy, sm, 1)
        end = datetime(ey, em, 28)
        if start <= date <= end:
            return True
    return False


def load_ao_archive() -> dict[str, float]:
    with AO_ARCHIVE_PATH.open() as f:
        raw = json.load(f)
    return {str(k): float(v) for k, v in raw.items()}


def load_outbreaks() -> list[dict]:
    with OUTBREAK_DB.open() as f:
        return json.load(f)


def mean_window(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def get_weighted_ao_features(
    center_date: datetime, ao_archive: dict[str, float], window_days: int, decay: float
) -> dict[str, float | int] | None:
    ao_vals: list[float] = []
    weights: list[float] = []
    for d in range(1, window_days + 1):
        check = center_date - timedelta(days=d)
        ds = check.strftime("%Y-%m-%d")
        if ds in ao_archive:
            ao_vals.append(float(ao_archive[ds]))
            weights.append(math.exp(-decay * (d - 1)))

    if len(ao_vals) < max(3, window_days // 2):
        return None

    ao_arr = ao_vals
    w_arr = weights
    w_sum = sum(w_arr)
    if w_sum <= 0:
        return None
    w_arr = [w / w_sum for w in w_arr]

    recent_n = min(7, len(ao_arr))
    features: dict[str, float | int] = {}
    features["ao_wmean"] = float(sum(w_arr[i] * ao_arr[i] for i in range(len(ao_arr))))
    features["ao_wmin"] = float(min(ao_arr[:recent_n]))

    if len(ao_arr) >= 14:
        recent_weights = w_arr[:7]
        prior_weights = w_arr[7:14]
        rw_sum = sum(recent_weights)
        pw_sum = sum(prior_weights)
        recent_mean = sum(
            (recent_weights[i] / rw_sum) * ao_arr[i] for i in range(len(recent_weights))
        )
        prior_mean = sum(
            (prior_weights[i] / pw_sum) * ao_arr[7 + i] for i in range(len(prior_weights))
        )
        features["ao_wtrend"] = float(recent_mean - prior_mean)
    else:
        features["ao_wtrend"] = 0.0

    if len(ao_arr) >= 14:
        very_recent = mean_window(ao_arr[:3])
        recent = mean_window(ao_arr[3:8])
        prior = mean_window(ao_arr[8:14])
        features["ao_accel"] = float((very_recent - recent) - (recent - prior))
    else:
        mid = max(1, len(ao_arr) // 2)
        features["ao_accel"] = float(mean_window(ao_arr[:mid]) - mean_window(ao_arr[mid:]))

    if len(ao_arr) >= 4:
        features["ao_final3_vs_prior"] = float(
            mean_window(ao_arr[:3]) - mean_window(ao_arr[3:])
        )
    else:
        features["ao_final3_vs_prior"] = 0.0
    features["ao_accel_sign"] = int(float(features["ao_accel"]) < -0.1)

    max_plunge = 0.0
    if len(ao_arr) >= 8:
        # ao_arr[0] is D-1, so compare older values to more recent ones.
        for i in range(len(ao_arr) - 7):
            plunge = ao_arr[i + 7] - ao_arr[i]
            if plunge > max_plunge:
                max_plunge = plunge
    features["ao_max_plunge"] = float(max_plunge)
    features["ao_plunge_sig"] = int(max_plunge > 1.0)
    return features


def get_gulf_features_window(center_date: datetime, gulf_client: WeeklyOISSTArchive) -> dict[str, float | int]:
    gulf_vals: list[float] = []
    for weeks_back in range(1, 5):
        check = center_date - timedelta(weeks=weeks_back)
        iso = check.date().isocalendar()
        rec = gulf_client.get_week_anomaly(int(iso[0]), int(iso[1]))
        gulf_vals.append(float(rec.get("anomaly", 0.0)))
    gulf_max = max(gulf_vals) if gulf_vals else 0.0
    return {
        "gulf_max": float(gulf_max),
        "gulf_warm": int(gulf_max > 0.5),
    }


def get_season_features(center_date: datetime) -> dict[str, float | int]:
    doy = center_date.timetuple().tm_yday
    month = center_date.month
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


def build_records(
    outbreaks: list[dict],
    ao_archive: dict[str, float],
    gulf_client: WeeklyOISSTArchive,
    window_days: int,
    decay: float,
) -> tuple[list[dict], int, int]:
    records: list[dict] = []
    la_nina_outbreaks = [
        o for o in outbreaks if date_in_la_nina(datetime.strptime(o["date"], "%Y-%m-%d"))
    ]

    outbreak_count = 0
    for outbreak in la_nina_outbreaks:
        odate = datetime.strptime(outbreak["date"], "%Y-%m-%d")
        ao_feat = get_weighted_ao_features(odate, ao_archive, window_days, decay)
        if ao_feat is None:
            continue
        record = {"label": 1, "date": outbreak["date"], "name": outbreak["name"]}
        record.update(ao_feat)
        record.update(get_gulf_features_window(odate, gulf_client))
        record.update(get_season_features(odate))
        records.append(record)
        outbreak_count += 1

    quiet_count = 0
    for sy, sm, ey, em in LA_NINA_PERIODS:
        current = datetime(sy, sm, 15)
        end = datetime(ey, em, 15)
        while current <= end:
            ym = current.strftime("%Y-%m")
            is_outbreak_month = any(o["date"].startswith(ym) for o in outbreaks)
            if not is_outbreak_month:
                ao_feat = get_weighted_ao_features(current, ao_archive, window_days, decay)
                if ao_feat is not None:
                    record = {
                        "label": 0,
                        "date": current.strftime("%Y-%m-%d"),
                        "name": "QUIET",
                    }
                    record.update(ao_feat)
                    record.update(get_gulf_features_window(current, gulf_client))
                    record.update(get_season_features(current))
                    records.append(record)
                    quiet_count += 1
            if current.month == 12:
                current = datetime(current.year + 1, 1, 15)
            else:
                current = datetime(current.year, current.month + 1, 15)

    return records, outbreak_count, quiet_count


def stratified_kfold_indices(y: list[int], k: int = 5, seed: int = 42) -> list[tuple[list[int], list[int]]]:
    pos_idx = [i for i, label in enumerate(y) if label == 1]
    neg_idx = [i for i, label in enumerate(y) if label == 0]
    rng = random.Random(seed)
    rng.shuffle(pos_idx)
    rng.shuffle(neg_idx)

    pos_folds = [[] for _ in range(k)]
    neg_folds = [[] for _ in range(k)]
    for i, idx in enumerate(pos_idx):
        pos_folds[i % k].append(idx)
    for i, idx in enumerate(neg_idx):
        neg_folds[i % k].append(idx)

    folds: list[tuple[list[int], list[int]]] = []
    all_idx = set(range(len(y)))
    for fold_num in range(k):
        test = sorted(pos_folds[fold_num] + neg_folds[fold_num])
        train = sorted(all_idx - set(test))
        folds.append((train, test))
    return folds


def evaluate_records(records: list[dict], feature_cols: list[str]) -> tuple[list[float], float, float]:
    X_raw = [[float(record.get(col, 0.0)) for col in feature_cols] for record in records]
    y = [int(record["label"]) for record in records]
    folds = stratified_kfold_indices(y, k=5, seed=42)
    aucs: list[float] = []

    for fold_num, (train_idx, test_idx) in enumerate(folds):
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

    mean_auc = _mean(aucs)
    std_auc = _pstdev(aucs)
    return aucs, mean_auc, std_auc


def fit_full_model(records: list[dict], feature_cols: list[str]) -> list[tuple[str, float]]:
    X_raw = [[float(record.get(col, 0.0)) for col in feature_cols] for record in records]
    y = [int(record["label"]) for record in records]
    means, stds = _scale_fit(X_raw)
    X_scaled = _scale_apply(X_raw, means, stds)
    X_bias = _add_bias(X_scaled)
    weights = _fit_logistic(X_bias, y, seed=42)
    feature_weights = list(zip(feature_cols, weights[:-1]))
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
    gulf_client = WeeklyOISSTArchive(use_network=True)

    pr("=== PATH 1 DAILY WINDOW VALIDATION ===")
    pr("Testing recency-weighted daily windows before La Nina outbreaks")
    pr(f"Baseline Mean AUC: {BASELINE_AUC:.3f}")
    pr()
    pr("=== GRID SEARCH: window_days x decay ===")
    pr(f"{'Window':>8} {'Decay':>8} {'Mean AUC':>10} {'Std':>8}  Folds")
    pr("-" * 68)

    best_result: dict | None = None
    all_results: list[dict] = []

    for window_days in WINDOWS:
        for decay in DECAYS:
            records, outbreak_count, quiet_count = build_records(
                outbreaks, ao_archive, gulf_client, window_days, decay
            )
            if not records or outbreak_count < 5 or quiet_count < 5:
                continue

            aucs, mean_auc, std_auc = evaluate_records(records, FEATURE_COLS)
            if len(aucs) < 5:
                continue

            result = {
                "window_days": window_days,
                "decay": decay,
                "mean_auc": float(mean_auc),
                "std_auc": float(std_auc),
                "fold_aucs": [float(v) for v in aucs],
                "n_outbreak_windows": int(outbreak_count),
                "n_quiet_windows": int(quiet_count),
            }
            all_results.append(result)

            is_best = best_result is None or mean_auc > float(best_result["mean_auc"])
            if is_best:
                best_result = result

            fold_str = str([round(v, 3) for v in aucs])
            suffix = "  *** BEST" if is_best else ""
            pr(
                f"{window_days:>8} {decay:>8.2f} {mean_auc:>10.3f} "
                f"{std_auc:>8.3f}  {fold_str}{suffix}"
            )

    if best_result is None:
        pr()
        pr("No valid grid-search results were produced.")
        REPORT_PATH.write_text(buf.getvalue())
        return 1

    best_records, outbreak_count, quiet_count = build_records(
        outbreaks,
        ao_archive,
        gulf_client,
        int(best_result["window_days"]),
        float(best_result["decay"]),
    )
    importances = fit_full_model(best_records, FEATURE_COLS)
    top_features = importances[:6]
    best_result["top_features"] = {name: float(weight) for name, weight in top_features}
    best_result["n_outbreak_windows"] = int(outbreak_count)
    best_result["n_quiet_windows"] = int(quiet_count)

    beats_baseline = float(best_result["mean_auc"]) > BASELINE_AUC
    delta = float(best_result["mean_auc"]) - BASELINE_AUC

    pr()
    pr("=== BEST RESULT ===")
    pr(f"Window: {int(best_result['window_days'])} days")
    pr(f"Decay:  {float(best_result['decay']):.2f}")
    pr(
        f"AUC:    {float(best_result['mean_auc']):.3f} "
        f"(std={float(best_result['std_auc']):.3f})"
    )
    pr(f"Folds:  {[round(v, 3) for v in best_result['fold_aucs']]}")
    pr()
    if beats_baseline:
        pr(
            f"RESULT: PASS — weighted windows beat the {BASELINE_AUC:.3f} baseline "
            f"by {delta:.3f} AUC."
        )
    else:
        pr(
            f"RESULT: NO IMPROVEMENT — weighted windows miss the {BASELINE_AUC:.3f} "
            f"baseline by {abs(delta):.3f} AUC."
        )
    pr()
    pr("Top features:")
    for feature_name, weight in top_features[:6]:
        pr(f"  {feature_name:<20}: {weight:+.3f}")

    payload = {
        "baseline_auc": BASELINE_AUC,
        "beats_baseline": beats_baseline,
        "delta_vs_baseline": float(delta),
        "best": best_result,
        "all_results": all_results,
    }

    REPORT_PATH.write_text(buf.getvalue())
    REPORT_JSON_PATH.write_text(json.dumps(payload, indent=2))
    GRID_JSON_PATH.write_text(json.dumps(payload, indent=2))
    pr()
    pr(f"Saved to {REPORT_JSON_PATH.relative_to(ROOT)}")
    pr(f"Saved to {GRID_JSON_PATH.relative_to(ROOT)}")
    REPORT_PATH.write_text(buf.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
