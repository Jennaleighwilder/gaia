#!/usr/bin/env python3
"""
Path 1 with event-scale features: 35-day daily AO + 5-week Gulf OISST (lazy weekly cache).
La Niña months only; outbreak months use first corpus event date in that month as anchor.
Pure Python CV (same machinery as path1_validation).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.path1_validation import (  # noqa: E402
    LA_NINA_PERIODS,
    OUTBREAK_DB,
    _add_bias,
    _advance_month,
    _fit_logistic,
    _kfold_indices,
    _mean,
    _predict_proba,
    _pstdev,
    _roc_auc,
    _scale_apply,
    _scale_fit,
    _sep_sigma,
    _ym_leq,
)

RUNS = ROOT / "runs"
REPORT_TXT = RUNS / "path1_daily_report.txt"
REPORT_JSON = RUNS / "path1_daily_report.json"

FEATURE_COLS = [
    "ao_min_35d",
    "ao_trend_14d",
    "ao_trend_7d",
    "ao_plunge_14d",
    "ao_plunge_7d",
    "ao_days_negative",
    "ao_consecutive_negative",
    "gulf_max_anom_5wk",
    "gulf_mean_anom_5wk",
    "gulf_warm_pulse_5wk",
    "gulf_warming_trend",
    "season_score",
    "in_spring",
    "in_winter_outbreak_season",
]


def _season_scores(eval_date: datetime) -> tuple[float, int, int]:
    month = eval_date.month
    doy = eval_date.timetuple().tm_yday
    if 91 <= doy <= 135:
        season_score = 0.9
    elif 74 <= doy <= 151:
        season_score = 0.7
    elif doy >= 319:
        season_score = 0.6
    else:
        season_score = 0.1
    return season_score, int(month in (3, 4, 5)), int(month in (11, 12))


def _first_outbreak_in_month(outbreaks: list[dict], ym: str) -> dict | None:
    matches = [o for o in outbreaks if str(o.get("date", "")).startswith(ym)]
    if not matches:
        return None
    matches.sort(key=lambda o: o["date"])
    return matches[0]


def build_records(*, use_network: bool) -> list[dict]:
    from runtime.ingest.daily_ao_archive import DailyAOArchive
    from runtime.ingest.weekly_oisst_archive import WeeklyOISSTArchive

    with open(OUTBREAK_DB) as f:
        outbreaks = json.load(f)
    outbreak_months = {o["date"][:7] for o in outbreaks}

    ao_arc = DailyAOArchive(use_network=use_network)
    gulf_arc = WeeklyOISSTArchive(use_network=use_network)
    ao_data = ao_arc.fetch_full_archive()

    records: list[dict] = []
    for sy, sm, ey, em in LA_NINA_PERIODS:
        y, m = sy, sm
        while _ym_leq((y, m), (ey, em)):
            current = datetime(y, m, 15)
            ym = f"{y}-{m:02d}"
            is_ob = ym in outbreak_months
            if is_ob:
                entry = _first_outbreak_in_month(outbreaks, ym)
                eval_date = (
                    datetime.strptime(entry["date"], "%Y-%m-%d") if entry else current
                )
            else:
                eval_date = current

            ao_f = ao_arc.get_pre_outbreak_features(eval_date, ao_data)
            gulf_f = gulf_arc.get_pre_outbreak_gulf_features(eval_date, None)
            ss, sp, wo = _season_scores(eval_date)

            rec: dict = {"ym": ym, "outbreak": 1 if is_ob else 0, **ao_f}
            rec["gulf_max_anom_5wk"] = float(gulf_f.get("gulf_max_anom_5wk", 0))
            rec["gulf_mean_anom_5wk"] = float(gulf_f.get("gulf_mean_anom_5wk", 0))
            rec["gulf_warm_pulse_5wk"] = int(gulf_f.get("gulf_warm_pulse_5wk", 0))
            rec["gulf_warming_trend"] = float(gulf_f.get("gulf_warming_trend", 0))
            rec["season_score"] = ss
            rec["in_spring"] = sp
            rec["in_winter_outbreak_season"] = wo
            records.append(rec)

            y, m = _advance_month(y, m)
    return records


def _records_to_matrix(records: list[dict]) -> tuple[list[list[float]], list[int]]:
    X = [[float(r[c]) for c in FEATURE_COLS] for r in records]
    y = [int(r["outbreak"]) for r in records]
    return X, y


def run(*, use_network: bool) -> dict:
    lines: list[str] = []

    def pr(*a: object) -> None:
        s = " ".join(str(x) for x in a)
        print(s)
        lines.append(s)

    pr("=" * 72)
    pr("PATH 1 DAILY / WEEKLY FEATURES (La Niña domain)")
    pr("=" * 72)
    from runtime.ingest.era5_daily_ao import GLOBAL_EOF_LOADING_FILE

    if GLOBAL_EOF_LOADING_FILE.exists():
        pr(
            "NOTE: AO uses global La Niña ERA5 EOF (sign-fixed) + z-scored daily index; "
            "`daily_ao_archive.json` merges ERA5 days over monthly AO interpolation for gaps. "
            "Gulf: real OISST weekly ERDDAP `anom`."
        )
    else:
        pr(
            "NOTE: NOAA CPC daily AO ASCII is often 404. Without global ERA5 EOF, "
            "`ao_monthly.dat` interpolation may fill AO — sub-weekly structure is limited. "
            "Gulf: real OISST weekly ERDDAP `anom`."
        )
    pr("Loading archives (AO once; Gulf lazy per ISO week)...")
    records = build_records(use_network=use_network)
    pr(f"Rows: {len(records)}  outbreak months: {sum(r['outbreak'] for r in records)}")

    X_raw, y = _records_to_matrix(records)
    ob = [X_raw[i] for i in range(len(y)) if y[i] == 1]
    non = [X_raw[i] for i in range(len(y)) if y[i] == 0]

    pr()
    pr("=== FEATURE SEPARATION (σ vs non-outbreak) ===")
    pr(f"{'Feature':<28} {'Ob μ':>10} {'Non μ':>10} {'Sepσ':>8}")
    pr("-" * 58)
    for j, feat in enumerate(FEATURE_COLS):
        ov = [row[j] for row in ob]
        nv = [row[j] for row in non]
        sep = _sep_sigma(ov, nv) if ov and nv else 0.0
        pr(
            f"{feat:<28} {_mean(ov):>10.3f} {_mean(nv):>10.3f} {sep:>8.2f}"
        )

    n = len(records)
    k = 5
    folds = _kfold_indices(n, k, seed=42)
    cv_aucs: list[float] = []
    for train_idx, test_idx in folds:
        X_tr = [X_raw[i] for i in train_idx]
        y_tr = [y[i] for i in train_idx]
        X_te = [X_raw[i] for i in test_idx]
        y_te = [y[i] for i in test_idx]
        mu, sd = _scale_fit(X_tr)
        X_tr_s = _scale_apply(X_tr, mu, sd)
        X_te_s = _scale_apply(X_te, mu, sd)
        w = _fit_logistic(_add_bias(X_tr_s), y_tr, seed=42)
        p_te = _predict_proba(_add_bias(X_te_s), w)
        cv_aucs.append(_roc_auc(y_te, p_te))

    mean_auc = _mean(cv_aucs)
    std_auc = _pstdev(cv_aucs)
    pr()
    pr("=== 5-FOLD CV ROC-AUC (logistic, balanced) ===")
    pr(f"Per fold: {[round(a, 3) for a in cv_aucs]}")
    pr(f"Mean AUC: {mean_auc:.3f}  (std {std_auc:.3f})")

    if mean_auc >= 0.70:
        pr("RESULT: mean AUC >= 0.70 on this harness.")
    elif mean_auc >= 0.65:
        pr("RESULT: marginal (0.65–0.70).")
    else:
        pr("RESULT: mean AUC < 0.65 — discrimination not stable in this split.")

    mu, sd = _scale_fit(X_raw)
    X_s = _scale_apply(X_raw, mu, sd)
    w_full = _fit_logistic(_add_bias(X_s), y, seed=42)
    coefs = sorted(
        zip(FEATURE_COLS, w_full[:-1]),
        key=lambda t: abs(t[1]),
        reverse=True,
    )
    pr()
    pr("Top |weights| (full fit):")
    for name, c in coefs[:8]:
        pr(f"  {name:<28} {c:+.4f}")

    pr()
    pr("=== APRIL 27 2011 vs JANUARY 15 2011 ===")
    from runtime.ingest.daily_ao_archive import DailyAOArchive
    from runtime.ingest.weekly_oisst_archive import WeeklyOISSTArchive

    ao_a = DailyAOArchive(use_network=use_network)
    g_a = WeeklyOISSTArchive(use_network=use_network)
    ad = ao_a.fetch_full_archive()
    for label, d in [
        ("APR 27 2011 (Super Outbreak)", datetime(2011, 4, 27)),
        ("JAN 15 2011 (quiet, same La Niña)", datetime(2011, 1, 15)),
    ]:
        af = ao_a.get_pre_outbreak_features(d, ad)
        gf = g_a.get_pre_outbreak_gulf_features(d, None)
        pr(label)
        pr(f"  ao_min_35d={af.get('ao_min_35d'):.3f}  ao_trend_14d={af.get('ao_trend_14d'):+.3f}  "
           f"plunge_14d={af.get('ao_plunge_14d')}")
        pr(f"  gulf_max_5wk={gf.get('gulf_max_anom_5wk'):.3f}  warm_pulse_5wk={gf.get('gulf_warm_pulse_5wk')}")

    out = {
        "mean_auc": mean_auc,
        "std_auc": std_auc,
        "fold_aucs": cv_aucs,
        "n_months": n,
        "n_outbreaks": int(sum(y)),
        "feature_importances": {f: float(c) for f, c in coefs},
    }
    RUNS.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(out, indent=2))
    REPORT_TXT.write_text("\n".join(lines) + "\n")
    pr()
    pr(f"Wrote {REPORT_TXT} and {REPORT_JSON}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--offline",
        action="store_true",
        help="Do not fetch; use existing AO + weekly Gulf caches only",
    )
    args = ap.parse_args()
    run(use_network=not args.offline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
