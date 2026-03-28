# GAIA Build Spec And Test Record

Last updated: March 27, 2026

## 1. Build Summary

GAIA is a live atmospheric and terrain intelligence system for western North Carolina.

Current deployed surfaces:

- GitHub Pages dashboard: `https://jennaleighwilder.github.io/gaia/docs/index.html`
- Railway API: `https://web-production-ce417.up.railway.app`

Current repo state:

- Local `main`: `9f080c83`
- Remote `origin/main`: `9f080c83`

This means the current dashboard redesign and Railway API wiring are pushed.

## 2. Product Goal

GAIA answers one operational question:

"What does the atmosphere, terrain, and fire layer say is building right now in western North Carolina?"

It combines:

- large-scale atmosphere status
- radar availability
- Holler Siren landslide terrain intelligence
- fire detections and fire-weather risk

The dashboard is designed to explain the signal in plain English, not just display raw values.

## 3. System Surfaces

### Frontend

File:

- `/Users/jenniferwest/gaia/docs/index.html`

Purpose:

- public-facing dashboard on GitHub Pages
- neon high-contrast visual design
- plain-language explainers for every major section
- live polling every 5 minutes

### Backend

Primary API file:

- `/Users/jenniferwest/gaia/runtime/dashboard/public_api.py`

Purpose:

- serves `/health`
- serves `/api/status`
- serves `/api/bundle`
- serves `/api/holler_siren`
- serves `/api/fire`

### Fire Layer

Core files:

- `/Users/jenniferwest/gaia/scripts/fire/fire_ingest.py`
- `/Users/jenniferwest/gaia/scripts/fire/fire_risk_layer.py`

Purpose:

- ingest NASA FIRMS, SPC, NWS, drought proxy, and MTBS fire history
- build terrain fire-risk overlay
- identify double-threat cells where landslide and fire risk overlap

## 4. Data Inputs

### Atmospheric / GAIA status

- AO index
- Gulf SST anomaly
- radar status metadata

### Holler Siren

- baseline terrain cell model
- live rainfall-aware Holler Siren endpoint when available

### Fire Layer

- NASA FIRMS active fire detections
- NOAA SPC fire-weather outlook
- NWS Asheville observations
- drought proxy
- MTBS historical burns

## 5. Key Outputs

### Dashboard sections

- atmospheric regime
- fire layer
- Holler Siren
- radar and feed health
- validation and proof
- top exposed hollows
- top double-threat cells
- how-to-read guide

### API outputs

- `/health`
- `/api/status`
- `/api/bundle`
- `/api/holler_siren`
- `/api/fire`

## 6. Production Verification

Verified on March 28, 2026 UTC:

### GitHub Pages dashboard

- `GET https://jennaleighwilder.github.io/gaia/docs/index.html` returned `HTTP 200`
- Live page contains:
  - Railway source host `web-production-ce417.up.railway.app`
  - `Fire Layer`
  - `How To Read GAIA Fast`
  - the new explainer layout copy

### Railway API

- `GET /health` returned `HTTP 200`
- response:
  - `status: ok`
  - `timestamp: 2026-03-28T00:53:04.008610+00:00`

- `GET /api/bundle` returned `HTTP 200`
- live response included:
  - `fire.active_fires: 79`
  - `fire.alert_level: CRITICAL`
  - `fire.double_threat_cells: 75`
  - `status.gaia_status: DORMANT`
  - `status.holler_siren_baseline.alert_level: CLEAR`
  - `status.validation.holler_siren_auc: 0.842`
  - `status.validation.holler_siren_cells: 40453`
  - `status.validation.holler_siren_trained_on: 1804`

- `GET /api/fire` returned `HTTP 200`
- live response included:
  - `fire_alert_level: CRITICAL`
  - `active_fire_count: 79`
  - `double_threat_cells: 75`
  - current weather:
    - station: `KAVL (Asheville)`
    - temp: `68.0 F`
    - RH: `68.4%`
    - wind: `16.1 mph`
    - fire_weather_flag: `false`

### Top live double-threat cells

1. `35.2660, -82.2344`
2. `35.9128, -81.9575`
3. `35.1313, -82.5667`

## 7. Local Code Tests

### Syntax validation

Command run:

```bash
PYTHONPATH=/Users/jenniferwest/gaia python3 -m py_compile \
  /Users/jenniferwest/gaia/scripts/fire/fire_ingest.py \
  /Users/jenniferwest/gaia/scripts/fire/fire_risk_layer.py \
  /Users/jenniferwest/gaia/runtime/dashboard/public_api.py
```

Result:

- passed with exit code `0`

### Repo sync

Command run:

```bash
git rev-parse --short HEAD
git rev-parse --short origin/main
```

Result:

- both returned `9f080c83`

This confirms the current dashboard build is pushed.

## 8. Functional Test Matrix

### Dashboard routing

- test: GitHub Pages serves dashboard HTML
- result: pass

### Dashboard source wiring

- test: public HTML points to Railway API host
- result: pass

### Railway health route

- test: `/health`
- result: pass

### Railway bundle route

- test: `/api/bundle`
- result: pass

### Railway fire route

- test: `/api/fire`
- result: pass

### Fire layer integration

- test: bundle includes fire summary
- result: pass

### Holler Siren fallback behavior

- test: dashboard supports live endpoint failure and baseline fallback
- result: pass by design and production behavior

## 9. Known Constraints

- The live Holler Siren rainfall-aware endpoint can return temporary unavailability; the dashboard falls back to baseline terrain monitoring instead of showing fake data.
- The GAIA repo has unrelated untracked local files in the worktree, but they were not part of this dashboard push.

## 10. Whiteboard Thesis

GAIA is not "just a dashboard."

It is a layered operational surface where:

- atmosphere explains regime
- terrain explains where failure concentrates
- fire explains how Helene debris turns into a second hazard

The build is now live, pushed, and production-verified across GitHub Pages and Railway.
