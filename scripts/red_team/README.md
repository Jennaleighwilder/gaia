# GAIA red team (reviewer attacks)

Scripts **A–F** mirror the adversarial checklist in `GAIA_RED_TEAM.md`. They are meant to **surface problems early**, not to greenwash.

```bash
export PYTHONPATH="$PWD"
python scripts/red_team/run_all.py
```

Appends a timestamped block to `runs/red_team_report.txt` (create `runs/` if missing).

| Script | Addresses |
|--------|-----------|
| `test_a_contingency.py` | Biased corpus / need full 2×2, not list detection only |
| `test_b_radar_archive.py` | N=1 radar; sample 50 F3+ from `major_events_1950_present.json` until `replay_day` exists |
| `test_c_uvrk_acf.py` | Hurricane-originated UVRK parameters vs monthly outbreak labels |
| `test_d_nws_baseline.py` | 13 min vs major-supercell operational leads |
| `test_e_debris_location.py` | Debris gate vs Mayfield (replace placeholder coords with your log) |
| `test_f_era5_disclosure.py` | Archive vs real-time indices |

**Not automated here:** Attack 3 (UWyo STP retrospectively matches forecaster-visible soundings) — state explicitly in methods: *same data an operational forecaster could open; GAIA does not claim hidden information.*
