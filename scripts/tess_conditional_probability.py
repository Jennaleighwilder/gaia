"""
Conditional probability skill: P(outbreak month | TESS >= T) vs base rate, lift.

Raw TESS is a unitless composite — *not* P(outbreak). Brier skill on raw TESS vs
binary outbreak is therefore a mis-specified metric (reviewers are right to flag it).
This module records that explicitly and fits a simple Platt map so a *calibrated*
probability exists for fair Brier comparison (in-sample; cross-validate for papers).
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTBREAK_DB = ROOT / "data" / "outbreak_database.json"
CAL_PATH = ROOT / "data" / "tess_skill_calibration.json"


def _sigmoid(z: float) -> float:
    z = max(-40.0, min(40.0, z))
    return 1.0 / (1.0 + math.exp(-z))


def _brier(probs: list[float], actuals: list[int]) -> float:
    return sum((p - a) ** 2 for p, a in zip(probs, actuals)) / max(1, len(actuals))


def _fit_platt_grid(scores: list[float], actuals: list[int]) -> tuple[float, float, float]:
    """Coarse grid Platt scaling: p = sigmoid(a*s + b). Returns (a, b, brier)."""
    best_br = 1e9
    best_a, best_b = 0.0, 0.0
    for ai in range(-80, 81):
        a = ai * 0.125
        for bi in range(-120, 121):
            b = bi * 0.08
            probs = [_sigmoid(a * s + b) for s in scores]
            br = _brier(probs, actuals)
            if br < best_br:
                best_br = br
                best_a, best_b = a, b
    return best_a, best_b, best_br


def _rare_threshold_audit(rows: list[dict], levels: list[float]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for t in levels:
        above = [r for r in rows if r["score"] >= t]
        oa = sum(1 for r in above if r["outbreak"])
        n = len(above)
        out[f">={t:.2f}"] = {
            "n_months": n,
            "n_outbreak_months": oa,
            "precision_outbreak_month": round(oa / n, 4) if n else None,
            "note": "empty bin" if n == 0 else ("tiny sample" if n < 5 else ""),
        }
    return out


def build_month_rows(
    year0: int = 1995,
    year1: int = 2024,
    *,
    use_network: bool = False,
) -> list[dict]:
    from scripts.historical_tess import compute_tess_full

    with open(OUTBREAK_DB) as f:
        outbreaks = json.load(f)
    ob_ym = {o["date"][:7] for o in outbreaks}
    rows: list[dict] = []
    for y in range(year0, year1 + 1):
        for m in range(1, 13):
            d = datetime(y, m, 15)
            ym = f"{y}-{m:02d}"
            full = compute_tess_full(d, neutral=False, use_network=use_network)
            rows.append(
                {
                    "ym": ym,
                    "score": full["tess_score"],
                    "outbreak": ym in ob_ym,
                }
            )
    return rows


def compute_calibration_table(rows: list[dict]) -> dict:
    n = len(rows)
    ob = sum(1 for r in rows if r["outbreak"])
    base = ob / max(1, n)
    scores = [r["score"] for r in rows]
    actuals = [1 if r["outbreak"] else 0 for r in rows]
    b_model = _brier(scores, actuals)
    b_climo = _brier([base] * n, actuals)
    bss_raw = 1.0 - (b_model / b_climo) if b_climo > 1e-9 else 0.0

    platt_a, platt_b, b_platt = _fit_platt_grid(scores, actuals)
    platt_probs = [_sigmoid(platt_a * s + platt_b) for s in scores]
    bss_platt = 1.0 - (b_platt / b_climo) if b_climo > 1e-9 else 0.0

    rare_audit = _rare_threshold_audit(rows, [0.75, 0.80, 0.85, 0.90])

    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
    table: list[dict] = []
    for t in thresholds:
        above = [r for r in rows if r["score"] >= t]
        if not above:
            continue
        oa = sum(1 for r in above if r["outbreak"])
        p_t = oa / len(above)
        lift = p_t / base if base > 1e-9 else 0.0
        table.append(
            {
                "threshold": t,
                "n_months": len(above),
                "n_outbreaks": oa,
                "p_outbreak_given_t": round(p_t, 4),
                "lift": round(lift, 3),
                "far": round(1.0 - p_t, 4),
            }
        )

    return {
        "n_months": n,
        "n_outbreak_months": ob,
        "base_rate": round(base, 5),
        "brier_raw_tess": round(b_model, 5),
        "brier_climatology": round(b_climo, 5),
        "brier_skill_score_raw_tess": round(bss_raw, 4),
        "brier_note": (
            "Negative BSS on raw TESS is expected: TESS is not calibrated to P(outbreak). "
            "Do not cite raw Brier skill in a paper. Use threshold lift table + rare-bin audit, "
            "or Platt-calibrated Brier (in-sample; cross-validate for claims)."
        ),
        "platt_scaling": {
            "a": round(platt_a, 5),
            "b": round(platt_b, 5),
            "brier_platt_calibrated": round(b_platt, 5),
            "brier_skill_score_platt": round(bss_platt, 4),
            "caveat": "Fitted on same 1995–2024 months as evaluation; optimistic. Use k-fold CV for publication.",
        },
        "rare_threshold_audit": rare_audit,
        "threshold_rows": table,
    }


def refresh_calibration_file(*, use_network: bool = False) -> dict:
    rows = build_month_rows(use_network=use_network)
    cal = compute_calibration_table(rows)
    cal["generated_at"] = datetime.now(timezone.utc).isoformat()
    CAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    CAL_PATH.write_text(json.dumps(cal, indent=2) + "\n")
    return cal


def load_calibration() -> dict | None:
    if not CAL_PATH.exists():
        return None
    try:
        return json.loads(CAL_PATH.read_text())
    except json.JSONDecodeError:
        return None


def platt_outbreak_probability(tess_score: float) -> float | None:
    """Map raw TESS → P̂(outbreak month) using saved Platt parameters (in-sample fit)."""
    cal = load_calibration()
    if not cal:
        return None
    ps = cal.get("platt_scaling")
    if not ps:
        return None
    a = float(ps["a"])
    b = float(ps["b"])
    return round(float(_sigmoid(a * tess_score + b)), 4)


def lookup_conditional_for_tess(tess_score: float) -> dict:
    """
    Map current TESS to P(outbreak | TESS >= nearest calibrated threshold) and lift.
    """
    cal = load_calibration()
    if not cal or not cal.get("threshold_rows"):
        return {
            "conditional_probability": None,
            "lift_vs_climatology": None,
            "risk_statement": "Calibration file missing; run: python scripts/tess_conditional_probability.py --refresh",
            "threshold_used": None,
        }
    base = float(cal["base_rate"])
    rows = sorted(cal["threshold_rows"], key=lambda r: r["threshold"])
    best = min(rows, key=lambda r: abs(r["threshold"] - tess_score))
    t = best["threshold"]
    p = float(best["p_outbreak_given_t"])
    lift = float(best["lift"])
    stmt = (
        f"Among months with TESS ≥ {t:.2f}, major-outbreak months occurred "
        f"{lift:.1f}× more often than the all-month baseline ({base*100:.1f}% → {p*100:.1f}%)."
    )
    return {
        "conditional_probability": round(p, 4),
        "lift_vs_climatology": round(lift, 3),
        "risk_statement": stmt,
        "threshold_used": t,
        "base_rate": base,
    }


def print_report(cal: dict) -> None:
    print("=== CONDITIONAL PROBABILITY SKILL SCORE ===")
    print(f"Months: {cal['n_months']}  Outbreak months: {cal['n_outbreak_months']}")
    print(f"Base rate P(outbreak month): {cal['base_rate']:.4f}")
    print(f"Brier raw TESS (mis-specified forecast): {cal['brier_raw_tess']:.5f}  Brier (climo): {cal['brier_climatology']:.5f}")
    print(f"BSS raw TESS: {cal['brier_skill_score_raw_tess']:.4f}  ← do not cite as skill")
    ps = cal.get("platt_scaling", {})
    bp = ps.get("brier_platt_calibrated")
    bssp = ps.get("brier_skill_score_platt")
    if isinstance(bp, (int, float)) and isinstance(bssp, (int, float)):
        print(f"Brier Platt-calibrated: {bp:.5f}  BSS Platt (in-sample): {bssp:.4f}")
    else:
        print("Platt calibration: (unavailable)")
    print()
    print("Rare bins (FAR / Test-02 context):")
    for k, v in sorted(cal.get("rare_threshold_audit", {}).items()):
        print(f"  TESS {k}: n={v['n_months']} outbreak_months={v['n_outbreak_months']} prec={v['precision_outbreak_month']} {v.get('note','')}")
    print()
    print(f"{'Threshold':>10} {'Months≥T':>10} {'Outbreaks':>10} {'P(ob|T)':>10} {'Lift':>8} {'FAR':>8}")
    print("-" * 65)
    for r in cal["threshold_rows"]:
        flag = ""
        if 2.5 < r["lift"] < 6:
            flag = " ***"
        print(
            f"{r['threshold']:>10.2f} {r['n_months']:>10} {r['n_outbreaks']:>10} "
            f"{r['p_outbreak_given_t']:>10.3f} {r['lift']:>8.2f}x {r['far']:>8.1%}{flag}"
        )


def main() -> int:
    use_net = "--network" in sys.argv
    cal = refresh_calibration_file(use_network=use_net)
    print_report(cal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
