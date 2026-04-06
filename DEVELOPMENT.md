# GAIA Development

## Local Run

```bash
./scripts/run_gaia.sh
```

Local dashboard:

```text
http://127.0.0.1:5001
```

Alternative Flask run:

```bash
python -m runtime.dashboard.app
```

## Local Dependencies

```bash
.venv/bin/pip install -r requirements.txt -r requirements-optional.txt
```

## Railway / production API (live dashboard)

The static site in `docs/index.html` calls the API host in `const API` (currently Railway). **Background refresh (TESS, surface, FIRMS fire layer) only runs on that Python service**, not on GitHub Pages.

In the Railway project → **Variables**, add:

- **`FIRMS_MAP_KEY`** — NASA FIRMS map key (same as in local `.env.local`; never commit the value).
- Optional: **`GAIA_LIVE_REFRESH=1`** (default), **`GAIA_LIVE_FIRE_INTERVAL_SEC`** (default 900).

After saving variables, **redeploy** so gunicorn picks them up. Check logs for `FIRMS_MAP_KEY=set` and `Refreshed data/fire`. If the key is missing, logs show `FIRMS_MAP_KEY=MISSING` and FIRMS counts stay stale.
