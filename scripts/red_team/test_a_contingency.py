#!/usr/bin/env python3
"""
RED TEAM A: Full 2×2 contingency (monthly TESS vs catalog outbreak months).
Precision, recall, F1, MCC — not detection rate on a list alone.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime

import scripts.red_team._paths  # noqa: F401
from scripts.live_tess_score import compute_tess_score

OUTBREAK_DB = scripts.red_team._paths.ROOT / "data" / "outbreak_database.json"


def _mcc(tp: int, fp: int, tn: int, fn: int) -> float:
    num = tp * tn - fp * fn
    den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return num / den if den > 0 else 0.0


def _table_for_threshold(
    threshold: float, scores: list[tuple[str, float]], outbreak_months: set[str]
) -> dict:
    tp = fp = tn = fn = 0
    fp_examples: list[tuple[str, float]] = []
    for ym, score in scores:
        pred = score >= threshold
        actual = ym in outbreak_months
        if pred and actual:
            tp += 1
        elif pred and not actual:
            fp += 1
            fp_examples.append((ym, score))
        elif not pred and actual:
            fn += 1
        else:
            tn += 1
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return {
        "threshold": threshold,
        "TP": tp,
        "FP": fp,
        "TN": tn,
        "FN": fn,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "mcc": _mcc(tp, fp, tn, fn),
        "fp_examples": sorted(fp_examples, key=lambda x: -x[1])[:10],
    }


def main() -> int:
    print("=== RED TEAM A: FULL 2×2 CONTINGENCY TABLE ===")
    print("Corpus: months with ≥1 entry in data/outbreak_database.json (binary outbreak month).")
    print("Predictor: monthly historical TESS (v2) ≥ threshold.")
    print()
    if not OUTBREAK_DB.exists():
        print("RESULT: FAIL — outbreak_database.json missing")
        return 1
    with open(OUTBREAK_DB) as f:
        outbreaks = json.load(f)
    ob_ym = {o["date"][:7] for o in outbreaks}
    print(f"Unique outbreak months in catalog: {len(ob_ym)}")
    print()

    scores: list[tuple[str, float]] = []
    for year in range(1995, 2025):
        for month in range(1, 13):
            date = datetime(year, month, 15)
            ym = f"{year}-{month:02d}"
            scores.append((ym, compute_tess_score(date)))

    for thr in (0.80, 0.65, 0.50):
        t = _table_for_threshold(thr, scores, ob_ym)
        print(f"--- Threshold {thr:.2f} ---")
        print(f"TP={t['TP']} FP={t['FP']} TN={t['TN']} FN={t['FN']}")
        print(f"Precision={t['precision']:.3f}  Recall={t['recall']:.3f}  F1={t['f1']:.3f}  MCC={t['mcc']:.3f}")
        if t["FP"] + t["TP"] == 0:
            print("  (no positive predictions — precision undefined at this threshold)")
        if t["fp_examples"]:
            print("  Sample FP months (warned, no catalog outbreak):")
            for ym, sc in t["fp_examples"][:5]:
                print(f"    {ym}  TESS={sc:.3f}")
        print()

    print("RESULT: PASS — table printed (interpret MCC; biased corpus caveat still applies).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
