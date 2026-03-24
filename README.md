# GAIA — Severe Weather Detection for East Tennessee

**83.9% detection. 18.5% false alarms. 176 minutes lead time.**

Validated against 460 historical severe weather events (1996–2025). Built by The Forgotten Code Research Institute.

## Quick Start

```bash
# Start daemon + dashboard
./scripts/run_gaia.sh
```

Dashboard: http://127.0.0.1:5001

## Deployment

- **GitHub Pages:** In repo **Settings → Pages**, set source to branch **`main`** and folder **`/docs`** (recommended). This repo includes **`docs/.nojekyll`** and **`.nojekyll`** so Jekyll does not replace the site with `README.md`. The public dashboard is **`docs/index.html`** (full GAIA Weather Intelligence UI). Root **`index.html`** redirects to **`docs/index.html`** if you use **`/`** as the Pages folder.
- **Refresh live TESS on the static dashboard:** `python scripts/live_tess_score.py && python scripts/sync_docs_tess.py` then commit `docs/`.
- **Live Flask dashboard** (`/live`, TESS + ASOS + soundings): static hosting cannot run it; use `python -m runtime.dashboard.app` or your hosted stack.
- **Docs:** See `docs/GAIA_SYSTEM_SUMMARY.md` for full system description

## Performance vs NWS

| Metric | NWS | GAIA |
|--------|-----|------|
| Tornado false alarm rate | 75% | 18.5% |
| Average lead time | 13 min | 176 min |

## Contact

theforgottencode780@gmail.com | [theforgottencode.com](https://theforgottencode.com)
