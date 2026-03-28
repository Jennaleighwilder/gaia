GAIA is open methodology. The data pipeline, ingest scripts, and validation
approach are documented here. The trained model weights, scoring calibration,
and West Method implementation are proprietary to Jennifer Leigh West /
The Forgotten Code Research Institute and are not included in this repository.
© 2026 Jennifer Leigh West. All rights reserved.

# GAIA — Severe Weather Detection for East Tennessee

**83.9% detection. 18.5% false alarms. 176 minutes lead time.**

Validated against 460 historical severe weather events (1996–2025). Built by The Forgotten Code Research Institute.

## Quick Start

```bash
# Start daemon + dashboard
./scripts/run_gaia.sh
```

Dashboard: http://127.0.0.1:5001

Core web deploys install [requirements.txt](/Users/jenniferwest/gaia/requirements.txt). For heavier local science/radar tooling, add [requirements-optional.txt](/Users/jenniferwest/gaia/requirements-optional.txt):

```bash
.venv/bin/pip install -r requirements.txt -r requirements-optional.txt
```

## Fire Layer Setup

```bash
cp .env.example .env.local
# then paste your NASA FIRMS MAP_KEY into .env.local

PYTHONPATH=/Users/jenniferwest/gaia .venv/bin/python scripts/fire/fire_ingest.py
PYTHONPATH=/Users/jenniferwest/gaia .venv/bin/python scripts/fire/fire_risk_layer.py
```

Get a free FIRMS key at https://firms.modaps.eosdis.nasa.gov/api/

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
