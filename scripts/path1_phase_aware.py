#!/usr/bin/env python3
from __future__ import annotations

import json
import random
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.ingest.weekly_oisst_archive import WeeklyOISSTArchive
from scripts.path1_allphase_validation import get_enso_phase, load_oni_monthly, month_last_day
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
REPORT_PATH = RUNS / "path1_phase_aware_report.txt"
REPORT_JSON_PATH = RUNS / "path1_phase_aware_report.json"
WINDOW_DAYS = 14
DECAY = 0.20
PHASES = ["LA_NINA", "EL_NINO", "NEUTRAL", "ALL"]


def build_phase_corpus(*, use_network: bool = False) -> tuple[list[dict], list[dict]]:
    ao_archive = load_ao_archive()
    outbreaks = load_outbreaks()
    oni_lookup = load_oni_monthly()
    gulf_client = WeeklyOISSTArchive(use_network=use_network)

    outbreak_years = {int(row["date"][:4]) for row in outbreaks}
    min_year = min(outbreak_years)
    max_year = max(outbreak_years)
    quiet_years = [year for year in range(min_year, max_year + 1) if year not in outbreak_years]
    rng = random.Random(42)

    outbreak_records: list[dict] = []
    control_records: list[dict] = []
    for outbreak in outbreaks:
        group_id = f"{outbreak['date']}::{outbreak['name']}"
        odate = datetime.strptime(outbreak["date"], "%Y-%m-%d")
        ao_feat = get_weighted_ao_features(odate, ao_archive, WINDOW_DAYS, DECAY)
        if ao_feat is None:
            continue

        phase, oni = get_enso_phase(oni_lookup, odate.year, odate.month)
        outbreak_record = {
            "group_id": group_id,
            "label": 1,
            "phase": phase,
            "oni": oni,
            "date": outbreak["date"],
            "name": outbreak["name"],
        }
        outbreak_record.update(ao_feat)
        outbreak_record.update(get_gulf_features_window(odate, gulf_client))
        outbreak_record.update(get_season_features(odate))
        outbreak_records.append(outbreak_record)

        candidate_years = [year for year in quiet_years if abs(year - odate.year) >= 2]
        rng.shuffle(candidate_years)
        added = 0
        for control_year in candidate_years:
            cday = min(odate.day, month_last_day(control_year, odate.month))
            cdate = datetime(control_year, odate.month, cday)
            c_feat = get_weighted_ao_features(cdate, ao_archive, WINDOW_DAYS, DECAY)
            if c_feat is None:
                continue
            c_phase, c_oni = get_enso_phase(oni_lookup, control_year, odate.month)
            control_record = {
                "group_id": group_id,
                "label": 0,
                "phase": c_phase,
                "oni": c_oni,
                "date": cdate.strftime("%Y-%m-%d"),
                "name": "CONTROL",
                "matched_to": outbreak["name"],
            }
            control_record.update(c_feat)
            control_record.update(get_gulf_features_window(cdate, gulf_client))
            control_record.update(get_season_features(cdate))
            control_records.append(control_record)
            added += 1
            if added >= 5:
                break
    return outbreak_records, control_records


def build_records_for_phase(phase: str, *, use_network: bool = False) -> list[dict]:
    ao_archive = load_ao_archive()
    outbreaks = load_outbreaks()
    oni_lookup = load_oni_monthly()
    gulf_client = WeeklyOISSTArchive(use_network=use_network)

    outbreak_years = {int(row["date"][:4]) for row in outbreaks}
    min_year = min(outbreak_years)
    max_year = max(outbreak_years)
    quiet_years = [year for year in range(min_year, max_year + 1) if year not in outbreak_years]
    rng = random.Random(42)
    records: list[dict] = []

    for outbreak in outbreaks:
        odate = datetime.strptime(outbreak["date"], "%Y-%m-%d")
        outbreak_phase, oni = get_enso_phase(oni_lookup, odate.year, odate.month)
        if outbreak_phase != phase:
            continue

        group_id = f"{outbreak['date']}::{outbreak['name']}"
        ao_feat = get_weighted_ao_features(odate, ao_archive, WINDOW_DAYS, DECAY)
        if ao_feat is None:
            continue

        outbreak_record = {
            "group_id": group_id,
            "label": 1,
            "phase": outbreak_phase,
            "oni": oni,
            "date": outbreak["date"],
            "name": outbreak["name"],
        }
        outbreak_record.update(ao_feat)
        outbreak_record.update(get_gulf_features_window(odate, gulf_client))
        outbreak_record.update(get_season_features(odate))
        records.append(outbreak_record)

        candidate_years = []
        for control_year in quiet_years:
            if abs(control_year - odate.year) < 2:
                continue
            control_phase, _ = get_enso_phase(oni_lookup, control_year, odate.month)
            if control_phase == phase:
                candidate_years.append(control_year)
        rng.shuffle(candidate_years)

        added = 0
        for control_year in candidate_years:
            cday = min(odate.day, month_last_day(control_year, odate.month))
            cdate = datetime(control_year, odate.month, cday)
            c_feat = get_weighted_ao_features(cdate, ao_archive, WINDOW_DAYS, DECAY)
            if c_feat is None:
                continue
            _, c_oni = get_enso_phase(oni_lookup, control_year, odate.month)
            control_record = {
                "group_id": group_id,
                "label": 0,
                "phase": phase,
                "oni": c_oni,
                "date": cdate.strftime("%Y-%m-%d"),
                "name": "CONTROL",
                "matched_to": outbreak["name"],
            }
            control_record.update(c_feat)
            control_record.update(get_gulf_features_window(cdate, gulf_client))
            control_record.update(get_season_features(cdate))
            records.append(control_record)
            added += 1
            if added >= 5:
                break
    return records


def filter_phase_records(
    outbreak_records: list[dict], control_records: list[dict], phase: str
) -> list[dict]:
    if phase == "ALL":
        return outbreak_records + control_records
    phase_outbreaks = [row for row in outbreak_records if row["phase"] == phase]
    group_ids = {row["group_id"] for row in phase_outbreaks}
    phase_controls = [
        row for row in control_records if row["group_id"] in group_ids and row["phase"] == phase
    ]
    return phase_outbreaks + phase_controls


def group_folds(group_ids: list[str], *, seed: int = 42) -> tuple[str, list[list[str]]]:
    ids = list(group_ids)
    random.Random(seed).shuffle(ids)
    if len(ids) < 10:
        return "LOO-group", [[group_id] for group_id in ids]
    folds = [[] for _ in range(5)]
    for idx, group_id in enumerate(ids):
        folds[idx % 5].append(group_id)
    return "5-fold-grouped", folds


def evaluate_grouped_records(records: list[dict]) -> dict | None:
    if not records:
        return None
    group_ids = sorted({row["group_id"] for row in records if row["label"] == 1})
    if len(group_ids) < 2:
        return None

    fold_name, fold_groups = group_folds(group_ids, seed=42)
    aucs: list[float] = []
    X_raw = [[float(row.get(col, 0.0)) for col in FEATURE_COLS] for row in records]
    y = [int(row["label"]) for row in records]

    for fold_num, test_groups in enumerate(fold_groups):
        test_group_set = set(test_groups)
        train_idx = [i for i, row in enumerate(records) if row["group_id"] not in test_group_set]
        test_idx = [i for i, row in enumerate(records) if row["group_id"] in test_group_set]
        if not train_idx or not test_idx:
            continue
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

    if not aucs:
        return None
    return {
        "cv": fold_name,
        "fold_aucs": [float(value) for value in aucs],
        "mean_auc": float(_mean(aucs)),
        "std_auc": float(_pstdev(aucs)),
        "n_records": len(records),
        "n_outbreaks": int(sum(row["label"] for row in records)),
        "n_controls": int(sum(1 - row["label"] for row in records)),
    }


def fit_full_model(records: list[dict]) -> list[tuple[str, float]]:
    X_raw = [[float(row.get(col, 0.0)) for col in FEATURE_COLS] for row in records]
    y = [int(row["label"]) for row in records]
    means, stds = _scale_fit(X_raw)
    X_scaled = _scale_apply(X_raw, means, stds)
    weights = _fit_logistic(_add_bias(X_scaled), y, seed=42)
    feature_weights = list(zip(FEATURE_COLS, weights[:-1]))
    feature_weights.sort(key=lambda item: abs(item[1]), reverse=True)
    return feature_weights


def main() -> int:
    RUNS.mkdir(exist_ok=True)
    buf = StringIO()

    def pr(line: str = "") -> None:
        print(line)
        buf.write(line + "\n")

    outbreak_records, control_records = build_phase_corpus(use_network=False)
    all_records = outbreak_records + control_records

    pr("=== PHASE-AWARE MODELS ===")
    pr(f"Window={WINDOW_DAYS} decay={DECAY:.2f}")
    pr(f"Total records: {len(all_records)}")
    pr(f"Total outbreaks: {sum(row['label'] for row in all_records)}")
    pr()

    results: dict[str, dict] = {}
    for phase in PHASES:
        records = (
            outbreak_records + control_records
            if phase == "ALL"
            else build_records_for_phase(phase, use_network=False)
        )
        result = evaluate_grouped_records(records)
        pr(f"{phase}:")
        if result is None:
            pr("  insufficient outbreaks to validate")
            pr()
            continue
        top_features = fit_full_model(records)[:4]
        result["top_features"] = {name: float(weight) for name, weight in top_features}
        results[phase] = result
        status = (
            "PASS"
            if result["mean_auc"] >= 0.70
            else "MARGINAL"
            if result["mean_auc"] >= 0.60
            else "FAIL"
        )
        pr(
            f"  {result['cv']} n_out={result['n_outbreaks']} n_ctrl={result['n_controls']}: "
            f"AUC={result['mean_auc']:.3f} std={result['std_auc']:.3f} [{status}]"
        )
        pr(f"  Folds: {[round(value, 3) for value in result['fold_aucs']]}")
        pr(
            f"  Top features: "
            f"{[(name, round(weight, 3)) for name, weight in top_features]}"
        )
        pr()

    REPORT_PATH.write_text(buf.getvalue())
    REPORT_JSON_PATH.write_text(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
