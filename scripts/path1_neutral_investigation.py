#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.path1_daily_window_validation import FEATURE_COLS
from scripts.path1_phase_aware import (
    build_phase_corpus,
    build_records_for_phase,
    evaluate_grouped_records,
    fit_full_model,
)
from scripts.path1_validation import _mean, _pstdev

RUNS = ROOT / "runs"
REPORT_PATH = RUNS / "path1_neutral_report.txt"
REPORT_JSON_PATH = RUNS / "path1_neutral_report.json"


def mean(xs: list[float]) -> float:
    return float(_mean(xs)) if xs else 0.0


def main() -> int:
    RUNS.mkdir(exist_ok=True)
    buf = StringIO()

    def pr(line: str = "") -> None:
        print(line)
        buf.write(line + "\n")

    outbreak_records, control_records = build_phase_corpus(use_network=False)
    records = build_records_for_phase("NEUTRAL", use_network=False)
    outbreaks = [row for row in records if row["label"] == 1]
    controls = [row for row in records if row["label"] == 0]
    result = evaluate_grouped_records(records)
    top_features = fit_full_model(records)

    pr("=== NEUTRAL OUTBREAK SIGNAL ANALYSIS ===")
    pr(f"Neutral outbreaks: {len(outbreaks)}")
    pr(f"Matched neutral controls: {len(controls)}")
    if result:
        pr(
            f"Neutral grouped CV: AUC={result['mean_auc']:.3f} "
            f"std={result['std_auc']:.3f} folds={[round(v, 3) for v in result['fold_aucs']]}"
        )
    pr()
    pr("Feature deltas (outbreak - control):")

    feature_rows: list[dict] = []
    ao_family = {
        "ao_wmean",
        "ao_wmin",
        "ao_wtrend",
        "ao_accel",
        "ao_accel_sign",
        "ao_final3_vs_prior",
        "ao_max_plunge",
        "ao_plunge_sig",
    }
    gulf_family = {"gulf_max", "gulf_warm"}
    season_family = {"in_spring", "in_peak", "season_score"}

    for feature in FEATURE_COLS:
        outbreak_vals = [float(row.get(feature, 0.0)) for row in outbreaks]
        control_vals = [float(row.get(feature, 0.0)) for row in controls]
        delta = mean(outbreak_vals) - mean(control_vals)
        sd = float(_pstdev(control_vals)) if control_vals else 0.0
        sep = delta / sd if sd > 1e-9 else 0.0
        feature_rows.append(
            {
                "feature": feature,
                "outbreak_mean": mean(outbreak_vals),
                "control_mean": mean(control_vals),
                "delta": delta,
                "sep_sigma": sep,
            }
        )
    feature_rows.sort(key=lambda row: abs(row["delta"]), reverse=True)

    for row in feature_rows:
        pr(
            f"  {row['feature']:<18} ob={row['outbreak_mean']:+.3f} "
            f"ctrl={row['control_mean']:+.3f} delta={row['delta']:+.3f} "
            f"sep={row['sep_sigma']:+.2f}σ"
        )

    pr()
    pr("Sample neutral outbreak windows:")
    for row in sorted(outbreaks, key=lambda item: item["date"])[:15]:
        season = (
            "spring"
            if row["in_spring"]
            else "peak"
            if row["in_peak"]
            else "winter"
            if row["season_score"] >= 0.6
            else "other"
        )
        pr(
            f"  {row['date']} {row['name'][:28]:<28} "
            f"ao_wmin={row['ao_wmin']:+.2f} ao_wtrend={row['ao_wtrend']:+.2f} "
            f"ao_accel={row['ao_accel']:+.2f} final3={row['ao_final3_vs_prior']:+.2f} "
            f"gulf={row['gulf_max']:+.2f} season={season}"
        )

    ao_weight = sum(abs(weight) for name, weight in top_features if name in ao_family)
    gulf_weight = sum(abs(weight) for name, weight in top_features if name in gulf_family)
    season_weight = sum(abs(weight) for name, weight in top_features if name in season_family)

    if result and result["mean_auc"] < 0.60 and ao_weight >= gulf_weight + season_weight:
        interpretation = "AO-only framing is likely the wrong primary discriminator for neutral outbreaks."
    elif result and result["mean_auc"] < 0.60:
        interpretation = "Neutral outbreaks are not well-separated by this AO/Gulf/season package; another field likely matters more."
    else:
        interpretation = "Neutral outbreaks show some discrimination, but the driver still needs a clearer mechanistic test."

    pr()
    pr("Interpretation:")
    pr(f"  {interpretation}")
    pr(
        f"  Top coefficients: {[(name, round(weight, 3)) for name, weight in top_features[:6]]}"
    )

    payload = {
        "neutral_cv": result,
        "top_features": {name: float(weight) for name, weight in top_features[:8]},
        "feature_deltas": feature_rows,
        "interpretation": interpretation,
    }
    REPORT_PATH.write_text(buf.getvalue())
    REPORT_JSON_PATH.write_text(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
