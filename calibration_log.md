# GAIA Phase 7c — Veto Calibration Log

Jennifer Leigh West | The Forgotten Code Research Institute

## Dewpoint Depression Veto

### Run 1: DD_VETO=15, DD_VETO_STRONG=20 (spec defaults)

| Metric | Value |
|--------|-------|
| Detection rate | 17/19 (89.5%) |
| False alarm rate | 10/17 (58.8%) |
| False alarms caught by DD veto | 0 |
| False alarms caught by calm wind veto | 0 |

**Real events caught (downgraded to MISS):**
- 2023-03-25 thunderstorm_wind → WATCH (dd=22°F at alarm)
- 2024-01-15 heavy_snow → WATCH (dd=20°F at alarm)

**Conclusion:** Threshold too aggressive. Must raise to preserve real events.

---

### Run 2: DD_VETO=23, DD_VETO_STRONG=25 (calibrated)

Raised thresholds so that:
- 2023-03-25 (dd=22) is NOT vetoed
- 2024-01-15 heavy_snow (dd=20) is NOT vetoed
- 2024-01-15 winter_storm (dd=16) was already preserved

| Metric | Value |
|--------|-------|
| Detection rate | 19/19 (100%) |
| False alarm rate | 9/17 (52.9%) |
| False alarms caught by DD veto | 0 |
| False alarms caught by calm wind veto | 1 (quiet_2022-07-03_GKT) |
| Real events NOT affected by veto | 13/19 |

**Note:** At DD=23, no false alarm has dd>23 at first alarm moment. The highest false-alarm dd is quiet_2020-04-18 (dd=22). Using DD=22 would catch that one but would also veto 2023-03-25 (dd=22). Threshold 23 preserves all real events.

---

## Calm Wind Veto

- Operates independently of DD veto.
- Requires wind_speed == 0 AND wind_direction == 0 at alarm time.
- **Fix:** Use `if wind_speed is None` (not `or`) when coalescing—0 is valid and was being dropped.
- Caught: quiet_2022-07-03_GKT (WARNING → WATCH).
- No real events have calm winds at alarm time.

---

## Final State (DD=23/25 + calm wind veto)

| Metric | Value |
|--------|-------|
| Detection rate | 19/19 (100%) |
| False alarm rate | 9/17 (52.9%) |
| DD veto catches | 0 |
| Calm wind veto catches | 1 |

---

## Build Order Status

- [x] Step 1: Dewpoint depression veto (governor.py)
- [x] Step 2: Backtest and calibrate
- [x] Calibration log
- [ ] Step 3: Harmonic engine (deferred)
- [ ] Step 4: Celestial → Harmonic feed (deferred)

*© 2026 Jennifer Leigh West | The Forgotten Code Research Institute*
