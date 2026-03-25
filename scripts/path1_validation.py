#!/usr/bin/env python3
"""
Path 1 validation: La Niña–only phase discrimination, variable screen, CV logistic composite,
threshold audit (n≥20, lift≥3, FAR<20%), honest monthly first-crossing lead times.

Writes runs/path1_validation_report.txt and prints to stdout.
No scikit-learn — pure Python (logistic + ROC AUC + K-fold).
"""
from __future__ import annotations

import argparse
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
RUNS = ROOT / "runs"
REPORT_PATH = RUNS / "path1_validation_report.txt"
REPORT_SCOUTS_PATH = RUNS / "path1_scouts_report.txt"
REPORT_REAL_FIELDS_PATH = RUNS / "path1_real_fields_report.txt"

LA_NINA_PERIODS = [
    (1998, 7, 2001, 2),
    (2007, 8, 2008, 6),
    (2010, 6, 2012, 3),
    (2017, 10, 2018, 4),
    (2020, 8, 2023, 3),
]

OUTBREAK_DB = ROOT / "data" / "outbreak_database.json"
MAX_MONTH_LOOKBACK = 24


def _advance_month(y: int, m: int) -> tuple[int, int]:
    if m == 12:
        return y + 1, 1
    return y, m + 1


def _ym_leq(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[0] or (a[0] == b[0] and a[1] <= b[1])


def _in_la_nina(y: int, m: int) -> bool:
    for sy, sm, ey, em in LA_NINA_PERIODS:
        if _ym_leq((sy, sm), (y, m)) and _ym_leq((y, m), (ey, em)):
            return True
    return False


def _la_nina_month_set() -> set[str]:
    s: set[str] = set()
    for sy, sm, ey, em in LA_NINA_PERIODS:
        y, m = sy, sm
        while _ym_leq((y, m), (ey, em)):
            s.add(f"{y}-{m:02d}")
            y, m = _advance_month(y, m)
    return s


FEATURE_KEYS_BASE = [
    "phase_anomaly",
    "ao_anomaly",
    "mei_anomaly",
    "pdo_anomaly",
    "pna_anomaly",
    "mjo_favorable",
    "gulf_sst",
    "spring",
]

FEATURE_KEYS_SCOUT = [
    "ao_daily",
    "ao_trend_14d",
    "ao_plunge",
    "scout_gulf_ssta",
    "gulf_sst_trend",
    "gulf_warm_pulse",
    "z500_proxy",
    "trough_deepening",
    "scout_mjo_amp",
    "scout_mjo_fav",
    "scout_mjo_approach",
    "scout_season_score",
    "scout_in_peak",
]

# NCEP Z500 + OISST anom + div200 + daily AO + season_score (no AO/Z500/Gulf proxies)
FEATURE_KEYS_REAL_FIELDS = [
    "phase_anomaly",
    "ao_anomaly",
    "mei_anomaly",
    "pdo_anomaly",
    "pna_anomaly",
    "mjo_favorable",
    "ao_daily",
    "ao_trend_14d",
    "ao_plunge",
    "scout_season_score",
    "scout_in_peak",
    "z500_anomaly_central_us",
    "z500_ridge_anomaly_rockies",
    "jet_amplification",
    "gulf_oisst_anomaly",
    "gulf_oisst_warm_pulse",
    "div_200mb_anomaly",
    "jet_exit_corridor",
]


def _collect_la_nina_records(
    outbreak_ym: set[str],
    *,
    use_scouts: bool,
    use_real_fields: bool,
    scout_network: bool,
) -> list[dict]:
    from scripts.historical_tess import compute_tess_full

    from runtime.ingest.divergence_client import DivergenceClient
    from runtime.ingest.gulf_oisst_client import GulfOISSTClient
    from runtime.ingest.scout_streams import ScoutStreams
    from runtime.ingest.z500_client import Z500Client

    scouts = (
        ScoutStreams(use_network=scout_network) if (use_scouts or use_real_fields) else None
    )
    zc = Z500Client(use_network=scout_network) if use_real_fields else None
    gc = GulfOISSTClient(use_network=scout_network) if use_real_fields else None
    dc = DivergenceClient(use_network=scout_network) if use_real_fields else None

    records: list[dict] = []
    for sy, sm, ey, em in LA_NINA_PERIODS:
        y, m = sy, sm
        while _ym_leq((y, m), (ey, em)):
            dt = datetime(y, m, 15)
            ym = f"{y}-{m:02d}"
            r = compute_tess_full(dt, use_network=False)
            an = r.get("anomalies") or {}
            row: dict = {
                "ym": ym,
                "y": y,
                "m": m,
                "outbreak": 1 if ym in outbreak_ym else 0,
                "phase_anomaly": float(r.get("phase_anomaly_score", 0)),
                "tess": float(r.get("tess_score", 0)),
                "ao_anomaly": float(an.get("ao", 0)),
                "mei_anomaly": float(an.get("mei", 0)),
                "pdo_anomaly": float(an.get("pdo", 0)),
                "pna_anomaly": float(an.get("pna", 0)),
                "mjo_favorable": 1 if r.get("mjo_favorable") else 0,
                "gulf_sst": float(r.get("gulf_sst_anomaly", 0)),
                "spring": 1 if m in (3, 4, 5) else 0,
            }
            if use_real_fields and zc is not None and gc is not None and dc is not None and scouts:
                ao = scouts.get_ao_plunge(dt)
                se = scouts.get_seasonal_loading(dt)
                z = zc.get_z500_anomaly(y, m)
                g = gc.get_gulf_sst_anomaly(y, m)
                d = dc.get_upper_divergence(y, m)
                row["ao_daily"] = float(ao.get("ao_daily", 0))
                row["ao_trend_14d"] = float(ao.get("ao_trend", 0))
                row["ao_plunge"] = 1.0 if ao.get("ao_plunge_detected") else 0.0
                row["scout_season_score"] = float(se.get("season_score", 0))
                row["scout_in_peak"] = 1.0 if se.get("in_peak_season") else 0.0
                row["z500_anomaly_central_us"] = float(z.get("z500_anomaly_central_us", 0))
                row["z500_ridge_anomaly_rockies"] = float(z.get("z500_ridge_anomaly_rockies", 0))
                row["jet_amplification"] = float(z.get("jet_amplification", 0))
                row["gulf_oisst_anomaly"] = float(g.get("gulf_oisst_anomaly", 0))
                row["gulf_oisst_warm_pulse"] = 1.0 if g.get("gulf_oisst_warm_pulse") else 0.0
                row["div_200mb_anomaly"] = float(d.get("div_200mb_anomaly", 0))
                row["jet_exit_corridor"] = 1.0 if d.get("jet_exit_over_corridor") else 0.0
            elif scouts is not None:
                for k, v in scouts.get_all_scouts(dt)["features"].items():
                    row[k] = float(v)
            records.append(row)
            y, m = _advance_month(y, m)
    return records


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _pstdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    v = sum((x - m) ** 2 for x in xs) / len(xs)
    return math.sqrt(v)


def _sep_sigma(ob: list[float], non: list[float]) -> float:
    if not ob or not non:
        return 0.0
    sd = _pstdev(non)
    if sd < 1e-9:
        return 0.0
    return (_mean(ob) - _mean(non)) / sd


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def _roc_auc(y: list[int], scores: list[float]) -> float:
    pos = [scores[i] for i in range(len(y)) if y[i] == 1]
    neg = [scores[i] for i in range(len(y)) if y[i] == 0]
    if not pos or not neg:
        return 0.5
    c = 0.0
    for p in pos:
        for n in neg:
            if p > n:
                c += 1.0
            elif p == n:
                c += 0.5
    return c / (len(pos) * len(neg))


def _scale_fit(X: list[list[float]]) -> tuple[list[float], list[float]]:
    if not X:
        return [], []
    d = len(X[0])
    means = [_mean([X[i][j] for i in range(len(X))]) for j in range(d)]
    stds = []
    for j in range(d):
        col = [X[i][j] for i in range(len(X))]
        s = _pstdev(col)
        stds.append(s if s > 1e-9 else 1.0)
    return means, stds


def _scale_apply(X: list[list[float]], means: list[float], stds: list[float]) -> list[list[float]]:
    out = []
    for row in X:
        out.append([(row[j] - means[j]) / stds[j] for j in range(len(row))])
    return out


def _add_bias(X: list[list[float]]) -> list[list[float]]:
    return [row + [1.0] for row in X]


def _fit_logistic(
    X: list[list[float]],
    y: list[int],
    *,
    epochs: int = 6000,
    lr: float = 0.35,
    l2: float = 1e-3,
    seed: int = 42,
) -> list[float]:
    rng = random.Random(seed)
    n = len(X)
    d = len(X[0])
    w = [rng.uniform(-0.05, 0.05) for _ in range(d)]
    n_pos = sum(y)
    n_neg = n - n_pos
    wp = n / (2.0 * n_pos) if n_pos else 1.0
    wn = n / (2.0 * n_neg) if n_neg else 1.0

    for _ in range(epochs):
        grad = [0.0] * d
        for i in range(n):
            z = sum(w[j] * X[i][j] for j in range(d))
            p = _sigmoid(z)
            wi = wp if y[i] == 1 else wn
            err = wi * (p - y[i])
            for j in range(d):
                grad[j] += err * X[i][j]
        for j in range(d):
            w[j] -= (lr / n) * grad[j] + lr * l2 * w[j]
    return w


def _predict_proba(X: list[list[float]], w: list[float]) -> list[float]:
    out = []
    for row in X:
        z = sum(w[j] * row[j] for j in range(len(row)))
        out.append(_sigmoid(z))
    return out


def _feature_keys(use_scouts: bool, use_real_fields: bool) -> list[str]:
    if use_real_fields:
        return list(FEATURE_KEYS_REAL_FIELDS)
    if use_scouts:
        return FEATURE_KEYS_BASE + FEATURE_KEYS_SCOUT
    return FEATURE_KEYS_BASE


def _records_to_X(records: list[dict], keys: list[str]) -> tuple[list[list[float]], list[int]]:
    X = [[float(r[k]) for k in keys] for r in records]
    y = [int(r["outbreak"]) for r in records]
    return X, y


def _kfold_indices(n: int, k: int, seed: int) -> list[tuple[list[int], list[int]]]:
    idx = list(range(n))
    random.Random(seed).shuffle(idx)
    folds: list[tuple[list[int], list[int]]] = []
    chunk = n // k
    for f in range(k):
        start = f * chunk
        end = (f + 1) * chunk if f < k - 1 else n
        test = idx[start:end]
        train = [i for i in idx if i not in test]
        folds.append((train, test))
    return folds


def run_steps(
    buf: StringIO,
    *,
    use_scouts: bool = False,
    use_real_fields: bool = False,
    scout_network: bool = True,
) -> dict:
    def pr(*a, **k):
        s = k.get("sep", " ")
        line = s.join(str(x) for x in a)
        print(line)
        buf.write(line + "\n")

    feature_keys = _feature_keys(use_scouts, use_real_fields)
    pr("=" * 72)
    if use_real_fields:
        pr("PATH 1 + REAL FIELDS (NCEP Z500, OISST Gulf anom, div200, daily AO, season_score)")
    elif use_scouts:
        pr("PATH 1 + SCOUTS (sub-monthly layer; Z500=AO proxy, Gulf=ERSST+trend)")
    else:
        pr("PATH 1 VALIDATION (La Niña months only for model training domain)")
    pr("=" * 72)

    with open(OUTBREAK_DB) as f:
        outbreaks = json.load(f)
    outbreak_ym = {o["date"][:7] for o in outbreaks}
    ln_set = _la_nina_month_set()

    # --- STEP 1 ---
    pr()
    pr("=== STEP 1: phase_anomaly_score within La Niña ===")
    all_ob_pa: list[float] = []
    all_non_pa: list[float] = []
    period_results = []

    for sy, sm, ey, em in LA_NINA_PERIODS:
        y, m = sy, sm
        ob_pa: list[float] = []
        non_pa: list[float] = []
        while _ym_leq((y, m), (ey, em)):
            dt = datetime(y, m, 15)
            ym = f"{y}-{m:02d}"
            from scripts.historical_tess import compute_tess_full

            r = compute_tess_full(dt, use_network=False)
            pa = float(r.get("phase_anomaly_score", 0))
            if ym in outbreak_ym:
                ob_pa.append(pa)
            else:
                non_pa.append(pa)
            y, m = _advance_month(y, m)
        if ob_pa and non_pa:
            sep = _sep_sigma(ob_pa, non_pa)
            label = "GOOD" if sep > 0.5 else "WEAK" if sep > 0 else "WRONG"
            pr(
                f"La Niña {sy}-{sm:02d} .. {ey}-{em:02d}: "
                f"ob μ={_mean(ob_pa):.3f} (n={len(ob_pa)})  "
                f"non μ={_mean(non_pa):.3f} (n={len(non_pa)})  "
                f"sep={sep:+.2f}σ  [{label}]"
            )
            all_ob_pa.extend(ob_pa)
            all_non_pa.extend(non_pa)
            period_results.append((sep, label))

    overall_sep = _sep_sigma(all_ob_pa, all_non_pa)
    pr()
    pr(f"OVERALL (all La Niña months pooled): sep={overall_sep:+.2f}σ")
    if overall_sep > 1.0:
        s1 = "STRONG pooled separation — phase_anomaly is a usable signal."
    elif overall_sep > 0.3:
        s1 = "WEAK/MODERATE — add other features (Step 2–3)."
    else:
        s1 = "NO/LITTLE pooled separation — headline claim cannot rest on phase_anomaly alone."
    pr("STEP 1 RESULT:", s1)

    # --- STEP 2 ---
    pr()
    pr("=== STEP 2: Variable discrimination (La Niña only) ===")
    records = _collect_la_nina_records(
        outbreak_ym,
        use_scouts=use_scouts,
        use_real_fields=use_real_fields,
        scout_network=scout_network,
    )
    ob = [r for r in records if r["outbreak"]]
    non = [r for r in records if not r["outbreak"]]
    pr(f"n months={len(records)}  outbreak months={sum(r['outbreak'] for r in records)}")
    pr(f"{'Variable':<18} {'Ob μ':>8} {'Non μ':>8} {'Sepσ':>8}  Signal")
    pr("-" * 60)
    var_rows = []
    var_list = [
        "tess",
        "phase_anomaly",
        "ao_anomaly",
        "mei_anomaly",
        "pdo_anomaly",
        "pna_anomaly",
        "mjo_favorable",
        "gulf_sst",
    ]
    if use_real_fields:
        var_list.extend(
            [
                "ao_daily",
                "z500_anomaly_central_us",
                "gulf_oisst_anomaly",
                "div_200mb_anomaly",
                "scout_season_score",
                "jet_amplification",
            ]
        )
    elif use_scouts:
        var_list.extend(
            [
                "ao_daily",
                "ao_plunge",
                "scout_gulf_ssta",
                "z500_proxy",
                "scout_mjo_approach",
                "scout_season_score",
            ]
        )
    for var in var_list:
        ov = [float(r[var]) for r in ob]
        nv = [float(r[var]) for r in non]
        if not ov or not nv:
            continue
        sep = _sep_sigma(ov, nv)
        sig = "STRONG" if sep > 1.0 else "MODERATE" if sep > 0.5 else "WEAK" if sep > 0 else "NEGATIVE"
        pr(f"{var:<18} {_mean(ov):>8.3f} {_mean(nv):>8.3f} {sep:>8.2f}  {sig}")
        var_rows.append((var, sep, sig))

    # --- STEP 3 ---
    pr()
    pr("=== STEP 3: 5-fold CV logistic on La Niña feature matrix ===")
    if use_real_fields:
        pr(f"(Features: {len(feature_keys)} cols — real Z500 / OISST / div200 + AO + season)")
    elif use_scouts:
        pr(f"(Features: {len(feature_keys)} cols incl. scouts)")
    X_raw, y = _records_to_X(records, feature_keys)
    n = len(records)
    k = 5
    if n < 30:
        pr("NOT ENOUGH ROWS for stable 5-fold CV.")
        cv_aucs = []
        mean_auc = 0.5
    else:
        folds = _kfold_indices(n, k, seed=42)
        cv_aucs = []
        held_lifts = []
        for train_idx, test_idx in folds:
            X_tr = [X_raw[i] for i in train_idx]
            y_tr = [y[i] for i in train_idx]
            X_te = [X_raw[i] for i in test_idx]
            y_te = [y[i] for i in test_idx]
            mu, sd = _scale_fit(X_tr)
            X_tr_s = _scale_apply(X_tr, mu, sd)
            X_te_s = _scale_apply(X_te, mu, sd)
            X_tr_b = _add_bias(X_tr_s)
            X_te_b = _add_bias(X_te_s)
            w = _fit_logistic(X_tr_b, y_tr, seed=42)
            p_te = _predict_proba(X_te_b, w)
            cv_aucs.append(_roc_auc(y_te, p_te))

            # Held-out lift: pick t on train (max lift s.t. n>=5, FAR<=0.35), eval test
            p_tr = _predict_proba(X_tr_b, w)
            base_tr = _mean([float(v) for v in y_tr])
            best_lift = 0.0
            best_t = 0.5
            for t in [i * 0.02 for i in range(5, 50)]:
                ab = [i for i in range(len(y_tr)) if p_tr[i] >= t]
                if len(ab) < 5:
                    continue
                ob_a = sum(y_tr[i] for i in ab)
                p_ob = ob_a / len(ab)
                far = 1.0 - p_ob
                lift = p_ob / base_tr if base_tr > 1e-9 else 0.0
                if far <= 0.35 and lift > best_lift:
                    best_lift = lift
                    best_t = t
            ab_te = [i for i in range(len(y_te)) if p_te[i] >= best_t]
            if ab_te:
                base_te = _mean([float(v) for v in y_te])
                ob_te = sum(y_te[i] for i in ab_te)
                lift_te = (ob_te / len(ab_te)) / base_te if base_te > 1e-9 else 0.0
                held_lifts.append(lift_te)
        mean_auc = _mean(cv_aucs)
        pr(f"CV ROC-AUC per fold: {[round(a, 3) for a in cv_aucs]}")
        pr(f"Mean CV AUC: {mean_auc:.3f}  (std {_pstdev(cv_aucs):.3f})")
        if held_lifts:
            pr(f"Mean held-out lift at fold-specific train-tuned thresholds: {_mean(held_lifts):.2f}x")

    if mean_auc > 0.70:
        auc_interp = "≥0.70 — defensible discrimination in CV (still validate on fully held-out years)."
    elif mean_auc > 0.65:
        auc_interp = "0.65–0.70 — marginal; tighten features / more data."
    else:
        auc_interp = "<0.65 — composite not reliably better than chance in this split; reframe claims."
    pr("STEP 3 RESULT:", auc_interp)

    # Full-data fit: threshold table (in-sample — for n≥20 / FAR scan)
    mu, sd = _scale_fit(X_raw)
    X_s = _scale_apply(X_raw, mu, sd)
    X_b = _add_bias(X_s)
    w_full = _fit_logistic(X_b, y, seed=42)
    probs_full = _predict_proba(X_b, w_full)
    base = _mean([float(v) for v in y])

    if use_scouts or use_real_fields:
        wc = sorted(
            zip(feature_keys, w_full[:-1]),
            key=lambda t: abs(t[1]),
            reverse=True,
        )[:3]
        top3 = ", ".join(f"{a}({b:+.3f})" for a, b in wc)
        pr()
        pr("=== EXTENDED MODEL REPORT (scouts or real fields) ===")
        label = "real fields + AO + season" if use_real_fields else "scouts"
        pr(f"1) Mean CV AUC ({label}): {mean_auc:.3f}  (baseline Path 1 only: ~0.693)")
        pr(
            f"2) Std of per-fold AUC: {_pstdev(cv_aucs):.3f}  (baseline ~0.232)"
            if cv_aucs
            else "2) Std of per-fold AUC: n/a (insufficient rows for CV)"
        )
        pr(f"3) Top 3 features by |logistic weight| (full fit): {top3}")
        if use_real_fields:
            pr("Note: Monthly NCEP/OISST fields — sub-monthly evolution not resolved here.")
        else:
            pr(
                "Note: Seasonal scout features align with MAM outbreak clustering;"
                " can distort CV when predicting outbreak months."
            )

    pr()
    pr("=== STEP 3b: In-sample probability thresholds (La Niña, full fit) ===")
    pr("(Used for n≥20 / lift≥3 / FAR<20% scan — optimistic; CV AUC above is primary.)")
    pr(f"{'Thr':>6} {'n≥':>5} {'Ob':>5} {'P(ob|T)':>8} {'Lift':>7} {'FAR':>7}  OK")
    pr("-" * 52)
    optimal_t = None
    for t in [i * 0.01 for i in range(5, 90)]:
        ab = [i for i in range(n) if probs_full[i] >= t]
        if len(ab) < 5:
            continue
        ob_a = sum(y[i] for i in ab)
        p_ob = ob_a / len(ab)
        lift = p_ob / base if base > 1e-9 else 0.0
        far = 1.0 - p_ob
        ok = len(ab) >= 20 and lift >= 3.0 and far <= 0.20
        flag = " ***" if ok else ""
        if len(ab) >= 20:
            pr(f"{t:>6.2f} {len(ab):>5} {ob_a:>5} {p_ob:>8.3f} {lift:>7.2f}x {far:>7.1%}{flag}")
        if ok and optimal_t is None:
            optimal_t = t

    # --- STEP 4: Honest lead — first month p >= T before outbreak month ---
    pr()
    pr("=== STEP 4: Honest monthly first-crossing (model probability) ===")
    T_use = optimal_t if optimal_t is not None else 0.25
    pr(f"Using probability threshold T = {T_use:.2f} (from Step 3b optimal *** if found, else 0.25)")
    pr("Rule: only outbreaks whose calendar month is inside a defined La Niña window.")
    pr("Lead = outbreak_date − 1st of month of the crossing edge closest to outbreak: smallest k with p(M−k)≥T and p(M−(k+1))<T.")
    pr("PRE-ELEVATED: p≥T for every month in lookback (cannot attribute a new crossing).")
    pr()

    from runtime.ingest.divergence_client import DivergenceClient
    from runtime.ingest.gulf_oisst_client import GulfOISSTClient
    from runtime.ingest.scout_streams import ScoutStreams
    from runtime.ingest.z500_client import Z500Client
    from scripts.historical_tess import compute_tess_full

    scout_reader = (
        ScoutStreams(use_network=scout_network) if (use_scouts or use_real_fields) else None
    )
    zc_rf = Z500Client(use_network=scout_network) if use_real_fields else None
    gc_rf = GulfOISSTClient(use_network=scout_network) if use_real_fields else None
    dc_rf = DivergenceClient(use_network=scout_network) if use_real_fields else None

    def features_for_month(yr: int, mo: int) -> list[float]:
        r = compute_tess_full(datetime(yr, mo, 15), use_network=False)
        an = r.get("anomalies") or {}
        if (
            use_real_fields
            and scout_reader is not None
            and zc_rf is not None
            and gc_rf is not None
            and dc_rf is not None
        ):
            dt = datetime(yr, mo, 15)
            ao = scout_reader.get_ao_plunge(dt)
            se = scout_reader.get_seasonal_loading(dt)
            z = zc_rf.get_z500_anomaly(yr, mo)
            g = gc_rf.get_gulf_sst_anomaly(yr, mo)
            d = dc_rf.get_upper_divergence(yr, mo)
            return [
                float(r.get("phase_anomaly_score", 0)),
                float(an.get("ao", 0)),
                float(an.get("mei", 0)),
                float(an.get("pdo", 0)),
                float(an.get("pna", 0)),
                1.0 if r.get("mjo_favorable") else 0.0,
                float(ao.get("ao_daily", 0)),
                float(ao.get("ao_trend", 0)),
                1.0 if ao.get("ao_plunge_detected") else 0.0,
                float(se.get("season_score", 0)),
                1.0 if se.get("in_peak_season") else 0.0,
                float(z.get("z500_anomaly_central_us", 0)),
                float(z.get("z500_ridge_anomaly_rockies", 0)),
                float(z.get("jet_amplification", 0)),
                float(g.get("gulf_oisst_anomaly", 0)),
                1.0 if g.get("gulf_oisst_warm_pulse") else 0.0,
                float(d.get("div_200mb_anomaly", 0)),
                1.0 if d.get("jet_exit_over_corridor") else 0.0,
            ]
        parts = [
            float(r.get("phase_anomaly_score", 0)),
            float(an.get("ao", 0)),
            float(an.get("mei", 0)),
            float(an.get("pdo", 0)),
            float(an.get("pna", 0)),
            1.0 if r.get("mjo_favorable") else 0.0,
            float(r.get("gulf_sst_anomaly", 0)),
            1.0 if mo in (3, 4, 5) else 0.0,
        ]
        if scout_reader is not None and not use_real_fields:
            sc = scout_reader.get_all_scouts(datetime(yr, mo, 15))["features"]
            parts.extend(float(sc[k]) for k in FEATURE_KEYS_SCOUT)
        return parts

    def prob_for_month(yr: int, mo: int) -> float:
        x = features_for_month(yr, mo)
        xs = [(x[j] - mu[j]) / sd[j] for j in range(len(x))]
        row = xs + [1.0]
        return _sigmoid(sum(w_full[j] * row[j] for j in range(len(row))))

    def month_k_before(oy: int, om: int, k: int) -> tuple[int, int]:
        """k months before outbreak month (k=1 → month immediately before outbreak)."""
        cy, cm = oy, om
        for _ in range(k):
            if cm == 1:
                cy, cm = cy - 1, 12
            else:
                cm -= 1
        return cy, cm

    leads: list[int] = []
    missed: list[str] = []
    pre_el: list[str] = []

    for ev in outbreaks:
        d0 = datetime.strptime(ev["date"], "%Y-%m-%d")
        oy, om = d0.year, d0.month
        if f"{oy}-{om:02d}" not in ln_set:
            continue
        # p at M-1, M-2, ... M-K
        probs: list[float] = []
        for k in range(1, MAX_MONTH_LOOKBACK + 1):
            yy, mm = month_k_before(oy, om, k)
            probs.append(prob_for_month(yy, mm))

        if not any(p >= T_use for p in probs):
            missed.append(ev["name"])
            pr(f"MISSED  {ev['date']}  {ev['name']}")
            continue
        if all(p >= T_use for p in probs):
            pre_el.append(ev["name"])
            pr(f"PRE-EL  {ev['date']}  {ev['name']}  (p≥T all {MAX_MONTH_LOOKBACK} mo back)")
            continue

        # Episode onset: smallest k (closest to outbreak) with p(M-k)≥T and p(M-(k+1))<T
        onset_k: int | None = None
        for k in range(1, MAX_MONTH_LOOKBACK + 1):
            pk = probs[k - 1]
            pk1 = probs[k] if k < MAX_MONTH_LOOKBACK else -1.0
            if pk >= T_use and pk1 < T_use:
                onset_k = k
                break
        if onset_k is None:
            missed.append(ev["name"])
            pr(f"MISSED  {ev['date']}  {ev['name']}  (no clean sub-T month before onset edge)")
            continue

        oy0, om0 = month_k_before(oy, om, onset_k)
        cross_first = datetime(oy0, om0, 1)
        lead_days = (d0 - cross_first).days
        leads.append(lead_days)
        pr(f"OK      {ev['date']}  {ev['name']}  onset=M-{onset_k} ({oy0}-{om0:02d})  lead≈{lead_days}d")

    pr()
    pr(f"La Niña-domain outbreaks evaluated: {len(leads)+len(missed)+len(pre_el)}")
    pr(f"  Countable first-crossing leads: {len(leads)}")
    pr(f"  Missed (no month ≥T before outbreak): {len(missed)}")
    pr(f"  Pre-elevated entire lookback: {len(pre_el)}")
    if leads:
        sl = sorted(leads)
        med = sl[len(sl) // 2]
        pr(f"  Median lead (valid only): {med} days")
        pr(f"  Mean: {_mean(leads):.0f}  Min: {min(leads)}  Max: {max(leads)}")
    pr("STEP 4 NOTE: Median uses only rows with a genuine sub-threshold gap before crossing (excl. PRE-EL).")

    # --- STEP 5 ---
    pr()
    pr("=== STEP 5: SUMMARY ===")
    pr("1) Phase anomaly within La Niña: pooled sep =", f"{overall_sep:+.2f}σ —", s1)
    pr("2) Strongest raw separators (Step 2):", ", ".join(f"{a}({b:+.2f}σ)" for a, b, _ in sorted(var_rows, key=lambda x: -x[1])[:4]) or "(n/a)")
    pr("3) Mean CV ROC-AUC:", f"{mean_auc:.3f} —", auc_interp)
    pr(
        "4) Operating threshold (in-sample) with n≥20 & lift≥3 & FAR≤20%:",
        f"{optimal_t:.3f}" if optimal_t is not None else "NONE found on La Niña sample — relax criteria or add predictors",
    )
    pr(
        "5) Honest median lead (La Niña outbreaks, valid crossings):",
        f"{sorted(leads)[len(leads)//2]} days" if leads else "n/a",
    )
    pr("6) 35-day claim: DEFENSIBLE only if CV AUC≥0.70 AND median lead≥14d AND held-out lift≥3x at n≥20 threshold — check above numbers.")
    pr()
    if mean_auc >= 0.70 and leads and sorted(leads)[len(leads) // 2] >= 14:
        pr("PATH 1 GATE: PASS (on stated metrics — peer review still requires full held-out years).")
    else:
        pr("PATH 1 GATE: FAIL or INCOMPLETE — frame a weaker claim or add data / refit.")

    if use_scouts or use_real_fields:
        pr()
        pr("=== CONTROL: April 2011 vs January 2011 (same La Niña) ===")
        pr("Scout composite at D−35, D−21, D−14, D−7, D−3 before each anchor date.")
        ctrl = ScoutStreams(use_network=scout_network)
        apr_scores: dict[int, float] = {}
        jan_scores: dict[int, float] = {}
        for label, target, bucket in [
            ("APR 27 2011 (Southeast Super Outbreak)", datetime(2011, 4, 27), apr_scores),
            ("JAN 15 2011 (quiet, same La Niña)", datetime(2011, 1, 15), jan_scores),
        ]:
            pr(f"--- {label} ---")
            for db in (35, 21, 14, 7, 3):
                chk = target - timedelta(days=db)
                out = ctrl.get_all_scouts(chk)
                bucket[db] = float(out["scout_composite_score"])
                pr(
                    f"  D-{db:2d} ({chk.strftime('%Y-%m-%d')}): "
                    f"composite={out['scout_composite_score']:.3f} "
                    f"{out['scout_alert_level']} {out['scout_key_signals']}"
                )
            pr()
        pr("4) April vs January scout composite: D-14 "
            f"Apr={apr_scores.get(14, 0):.3f} vs Jan={jan_scores.get(14, 0):.3f}; "
            f"D-7 Apr={apr_scores.get(7, 0):.3f} vs Jan={jan_scores.get(7, 0):.3f}")
        pr("5) Median honest lead (this run):", f"{sorted(leads)[len(leads)//2]} days" if leads else "n/a")
        if mean_auc > 0.70:
            pr("6) AUC > 0.70: revisit Path 1 gate text for median lead vs 35-day framing.")
        else:
            pr(
                "6) AUC < 0.70: 35-day month-ahead claim is not validated by this harness; "
                "radar + sounding layers remain the strongest independent results."
            )

        if use_real_fields:
            pr()
            pr("--- Real fields at probe month (calendar month of D−14 / D−7) ---")
            zc2 = Z500Client(use_network=scout_network)
            gc2 = GulfOISSTClient(use_network=scout_network)
            dc2 = DivergenceClient(use_network=scout_network)
            for label, target in [
                ("APR 27 2011", datetime(2011, 4, 27)),
                ("JAN 15 2011", datetime(2011, 1, 15)),
            ]:
                pr(f"  {label}:")
                for db in (14, 7):
                    chk = target - timedelta(days=db)
                    z = zc2.get_z500_anomaly(chk.year, chk.month)
                    # OISST cache keys use month-center day=15; align with Path 1 monthly rows
                    g = gc2.get_gulf_sst_anomaly(chk.year, chk.month, day=15)
                    d = dc2.get_upper_divergence(chk.year, chk.month)
                    pr(
                        f"    D-{db} (mo={chk.year}-{chk.month:02d}): "
                        f"Z500_c={z.get('z500_anomaly_central_us')} "
                        f"Gulf_anom={g.get('gulf_oisst_anomaly')} "
                        f"div_anom={d.get('div_200mb_anomaly')}"
                    )

    return {
        "step1_sep": overall_sep,
        "mean_cv_auc": mean_auc,
        "optimal_t": optimal_t,
        "median_lead_days": sorted(leads)[len(leads) // 2] if leads else None,
        "use_scouts": use_scouts,
        "use_real_fields": use_real_fields,
    }


def main() -> int:
    RUNS.mkdir(parents=True, exist_ok=True)
    ap = argparse.ArgumentParser(description="Path 1 La Niña validation harness")
    ap.add_argument(
        "--with-scouts",
        action="store_true",
        help="Add scout streams to the feature matrix; write path1_scouts_report.txt",
    )
    ap.add_argument(
        "--scout-offline",
        action="store_true",
        help="Scouts use cache only (no new HTTP for AO/Gulf/MJO)",
    )
    ap.add_argument(
        "--with-real-fields",
        action="store_true",
        help="NCEP Z500 + OISST Gulf + div200 + daily AO + season_score (implies network fetch)",
    )
    args = ap.parse_args()
    buf = StringIO()
    scout_net = not args.scout_offline
    use_real = bool(args.with_real_fields)
    use_scout = bool(args.with_scouts) or use_real
    run_steps(
        buf,
        use_scouts=use_scout,
        use_real_fields=use_real,
        scout_network=scout_net,
    )
    if use_real:
        out_path = REPORT_REAL_FIELDS_PATH
    elif args.with_scouts:
        out_path = REPORT_SCOUTS_PATH
    else:
        out_path = REPORT_PATH
    out_path.write_text(buf.getvalue())
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
