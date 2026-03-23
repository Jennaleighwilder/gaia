# GAIA Phase 7 — Cursor Handoff
## Siren Engine (7a) + Celestial Engine (7b)
## Jennifer Leigh West | The Forgotten Code Research Institute

---

## WHERE GAIA STANDS

```
Detection rate:     100% (19/19)
False alarm rate:   52.9% (9/17)
Lead time:          376 minutes average
Saddle detections:  19/19
```

## CURRENT STATE AFTER HANDOFF INTEGRATION

The handoff engines (new Siren + new Celestial) are **installed and scoring**:
- `siren_engine.py` — 7 channels, sound_baseline_speed=350 (East TN)
- `celestial_engine.py` — Kp, solar wind, IMF Bz, proton flux

Both are in **observation/context mode** (not voting in convergence):
- Siren: scored, exposed in output, excluded from saddle
- Celestial: CONTEXT engine, modifies thresholds (0.5→more sensitive, 0.3–0.5→slight, <0.2→less)

**Operational trial (SIREN_DAMPER + CELESTIAL_BOOST as convergence)** was reverted:
- False alarms increased 52.9% → 64.7%
- Likely causes: Celestial fetch fails in sandbox (403), so celestial=0; Siren as voter may add false convergence

**Next steps for Phase 7 operational:**
1. Run backtest with network enabled so Celestial gets live Kp/Bz
2. Or add historical Kp to national fixtures
3. Recalibrate SIREN_DAMPER thresholds (0.2, 0.3) on national sample

---

*© 2026 Jennifer Leigh West | The Forgotten Code Research Institute*
