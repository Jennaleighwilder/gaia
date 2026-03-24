# GAIA Phase 4 — Submission-ready validation (March 2026)

Static copy of results produced by repository scripts. Regenerate locally with:

- `python scripts/era5_outbreak_reverse_engineer.py` → `runs/era5_outbreak_tess.json` (gitignored)
- `python scripts/dualpol_debris_detector.py` → `runs/dualpol_mayfield_report.json` (gitignored)

## 1. ERA5 reverse-engineer — 35 outbreaks since 1990

- **Data:** Open-Meteo Archive API (ERA5-backed daily fields at outbreak-centric lat/lon).
- **Metric:** First calendar day in the 45-day pre-event window with **TESS ≥ 0.70** (loading layer from ERA5; origin/transport use documented seasonal priors — see script).
- **Outcomes:** **17 / 35** outbreaks with a defined first-fire date.
- **Median lead time (subset with fire):** **35.0 days**.

Full per-outbreak table is written by the script to `runs/era5_outbreak_tess_table.md` when you run it.

## 2. Dual-pol debris signature — Mayfield (Quad-State), 10 Dec 2021

- **Radar:** KPAH Level II, local archive under `tests/fixtures/nexrad_quadstate/`.
- **Window (UTC):** 2021-12-11 08:00–10:30 (Mayfield impact taken as **09:30 UTC** = 03:30 CST).
- **Confirmed hit:** `KPAH20211211_080315_V06`, sweep 2, within 40 km of Mayfield.
- **Fields:** Z_max **61.5 dBZ**, CC_min **0.208**, ZDR_median **0.22 dB**; velocity not available at the debris gate on that sweep (`rotation_available: false`).
- **Lead vs Mayfield impact:** **86.8 minutes**.
- **Lead vs NWS Paducah TOR (09:02 UTC):** **58.8 minutes**.

## 3. Quiet-day sanity (context)

On a high-TESS global day, **real soundings** can still show **zero CAPE / zero STP** regionally — separating **global loading** from **local instability** is intentional (UWyo + MetPy pipeline in `runtime/data/sounding_client.py`).

---

*The Forgotten Code Research Institute / GAIA*
