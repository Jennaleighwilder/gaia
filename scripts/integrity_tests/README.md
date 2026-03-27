# GAIA integrity tests

Eight scripts under `scripts/integrity_tests/` each print a single `RESULT:` line (`PASS`, `WARN`, or `FAIL`) plus supporting detail. They are meant to be **built and reviewed on a schedule**, not interpreted when tired.

## Run

From the repository root:

```bash
export PYTHONPATH="$PWD"
python scripts/integrity_tests/run_all.py
```

That appends a timestamped block to `runs/integrity_test_report.txt` (create the file on first run if needed).

To run one test:

```bash
PYTHONPATH="$PWD" python scripts/integrity_tests/test_01_time_shift.py
```

## Dependencies

- **Historical TESS** (`compute_tess_score`): monthly files in `data/global_indices/` (same layout as CPC/NOAA ASCII the project already vendors).
- **Outbreak catalog**: `data/outbreak_database.json` (names/dates/states; curated from the ERA5 outbreak list).
- **Leakage audit (test 04)**: optional `runs/backtest_results.json` or `runs/forward_test_results.json` with `event_time` and `observation_timestamps` fields.
- **Radar FAR (test 03)**: no `replay_day()` in `scripts/radar_storm_tracker.py` yet — test stays at `WARN` without importing Py-ART.

## Notes

- **TESS v2** uses phase-anomaly layers (24-month z-scores), UVRK blend, and offline MJO/Gulf loading (`use_network=False` in integrity runs). **Test 02** samples **unique (year, month)**; FAR target is **&lt; 15%** at TESS &gt; 0.80.
- **Calibration**: run `python scripts/tess_conditional_probability.py --refresh` to regenerate `data/tess_skill_calibration.json` (used for live `conditional_probability` / `risk_statement`).
- **Test 08** checks fixed radar–point geometry; actual storm motion at 08:03 UTC still belongs in case-study QA.
