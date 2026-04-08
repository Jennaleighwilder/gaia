# Ferry County — CWDG field & compliance (Phase 1 backend + Phase 2 Field PWA)

Production-oriented API for **road inventory (KMZ)**, **treatment logging**, **acreage math**, **GIS export (GeoJSON + KMZ)**, **reimbursement-ready records**, **match / Davis-Bacon flags**, **append-only audit log**, and **idempotent offline sync receipts**, plus a **field-facing PWA** (map, GPS, treatment form, offline sync queue).

**Authoritative spec (hardened):** [`docs/SPEC.md`](docs/SPEC.md)

The valuable surface area is **traceability**, **spatial deliverables** (annual layer), and **reimbursement evidence** — the Field app is the operator front-end to that backend.

## Requirements

- **Python 3.11–3.13** (avoid **3.14** for now — `pydantic-core` wheels often lag).
- **PostgreSQL + PostGIS** (`docker-compose.yml`).
- Copy `.env.example` → `.env` and set `DATABASE_URL`.

## Install & database

```bash
cd ferry_county
make install          # or: python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
make db-up            # Docker daemon must be running
export DATABASE_URL=postgresql+psycopg2://ferry:ferry@127.0.0.1:5434/ferry
make migrate
make test
```

## One-command vertical slice (smoke)

Imports KMZ bytes, logs a tiny treatment, prints reimbursement JSON + GeoJSON feature count — **no uvicorn required**:

```bash
export FERRY_KMZ=/absolute/path/to/FerryCounty_Complete_Roads_v2.kmz
make vertical-slice
# or: PYTHONPATH=. .venv/bin/python scripts/vertical_slice.py "$FERRY_KMZ"
```

## API server

```bash
export PYTHONPATH=.
uvicorn backend.main:app --reload --port 8090
```

## Phase 2 — Field PWA (Vite + MapLibre)

Local dev runs the UI on **5173** with `/api` proxied to **8090** (see `frontend/vite.config.js`). Set `CORS_ORIGINS` / `cors_origins` if you use a different origin.

```bash
# Terminal A: API
export PYTHONPATH=.
uvicorn backend.main:app --reload --port 8090

# Terminal B: frontend
cd frontend && npm ci && npm run dev
```

- **Unit tests (Vitest + Testing Library):** `cd frontend && npm test`
- **E2E (Playwright, mocked API):** `cd frontend && npx playwright install chromium && npm run e2e`
- **Production build:** `cd frontend && npm run build` — static assets use same-origin **`/api`** unless you set **`VITE_API_BASE`** (see `frontend/.env.example`).

## Deployed stack (Docker)

PostGIS-only (default, matches local `DATABASE_URL` on host port **5434**):

```bash
make db-up
```

Full stack — **API :8090**, **nginx + SPA :8080** (`/api` → API):

```bash
make stack-up
# UI: http://localhost:8080  — API: http://localhost:8090
```

Compose profile **`stack`** builds `Dockerfile` (API + migrations) and `frontend/Dockerfile` (static build + nginx). Override **`CORS_ORIGINS`** in `docker-compose.yml` or your environment for the real public URL.

## KMZ import (production default)

**Use multipart upload** (no server-side filesystem reads):

```http
POST /gis/import-kmz-upload
Content-Type: multipart/form-data
file=@FerryCounty_Complete_Roads_v2.kmz
```

**Path-based JSON import** (`POST /gis/import-kmz`) is **403 by default**. Enable only on trusted automation hosts:

- `ALLOW_KMZ_PATH_IMPORT=true`
- Optional jail: `KMZ_PATH_ALLOW_PREFIXES=/abs/dir1,/abs/dir2`

Check flags: `GET /gis/security-config`

### Stable road identity

`FerryCounty_Complete_Roads_v2.kmz` may omit Placemark `id`. The system uses **`source_feature_id`** = `fc_` + SHA-256(folder + name + WKT). **Never** key by road name alone.

## Waypoints (material / Buy America)

```http
POST /waypoints
Content-Type: application/json
X-Actor: david

{
  "road_id": 1,
  "lat": 48.55,
  "lon": -118.5,
  "waypoint_type": "material_site",
  "label": "Gravel staging",
  "buy_america_certified": true,
  "material_cost": 250,
  "vendor": "Example Supply"
}
```

- `GET /waypoints` — optional `road_id` filter
- Offline sync: `entity_type` **`waypoint`**, `operation` **`create`**, payload matches **`WaypointSyncPayload`**

## Attachment file blobs (local disk)

Multipart upload stores bytes under **`ATTACHMENT_STORAGE_DIR`** (content-addressed by SHA-256). No S3 required; use a persistent volume in Docker.

```http
POST /attachments/upload
Content-Type: multipart/form-data
X-Actor: david

file=@invoice.pdf
kind=invoice
treatment_id=42
```

- `GET /attachments/{id}/file` — download the stored blob
- `GET /attachments` — list metadata (optional `treatment_id` / `waypoint_id` filters)
- Legacy **`POST /attachments`** (JSON metadata only) remains for external storage URIs

## Field GPS tracks (evidence)

Record a path in the Field app; the server stores **`LINESTRING`**, **`calculated_miles`**, and **`raw_gps_log`**. Link a track to a treatment with **`track_id`** on treatment create (REST or sync).

```http
POST /tracks
Content-Type: application/json
X-Actor: david

{
  "road_id": 1,
  "points": [
    { "lon": -118.5, "lat": 48.55, "accuracy_m": 4.2 },
    { "lon": -118.51, "lat": 48.56 }
  ],
  "start_time": "2026-04-07T18:00:00Z",
  "end_time": "2026-04-07T18:05:00Z"
}
```

- `GET /tracks` — recent tracks (optional `road_id` filter)
- `GET /tracks/{id}` — detail + `raw_gps_log`

## Treatment + reimbursement record

```http
POST /treatments/roads/{road_id}
Content-Type: application/json
X-Actor: david

{
  "treatment_date": "2026-04-01",
  "miles_treated": 0.25,
  "treatment_type": "brush_clear",
  "contractor_invoice_amount": 2500,
  "amount_federal": 300,
  "amount_match": 100,
  "match_documented": true,
  "davis_bacon_certified": false
}
```

```http
GET /treatments/{id}/reimbursement
```

## Exports (annual spatial component)

- `GET /gis/export/geojson` — FeatureCollection, WGS84
- `GET /gis/export/kmz` — zipped `doc.kml`
- `GET /roads/geojson` — Field map layer: same geometries with **`treatment_status`** and **`is_grant_road`** (CEMP miles > 0) for client-side styling

## Compliance & reporting

- `GET /compliance/match-ratio` — aggregate **federal** vs **documentally matched** spend (active treatments), **match share %**, **compliant** if ≥ program minimum (default **25%**). Shown on the Field app **Compliance** card.
- `GET /compliance/export/geojson` and `GET /compliance/export/kmz` — query **`period_start`** / **`period_end`** (inclusive on `treatment_date`). Returns **MultiLineString** features from road geometry with treatment metadata (miles, acres, contractor, etc.) for **annual spatial** / USFS-style packages. Distinct from **`/gis/export/*`**, which exports the **road inventory**.
- `POST /compliance/quarterly-report` — body: quarter label, federal spend, match cash / in-kind, optional **submitted** + **submitted_date** + **notes**. Persists **`quarterly_financial_reports`** with computed **total_spend** and **match_ratio**.
- `GET /compliance/semi-annual-report?period_start=&period_end=` — JSON: miles, acres, road complete/partial counts, period **match_ratio**, treatment rows, waypoint sign/mile-marker counts, Davis-Bacon / Buy America tallies (USFS-style semi-annual fields).
- `GET /compliance/invoice-support?start=&end=&format=json|pdf|csv` — reimbursement line items (road, district, dates, miles, acres, GPS start/end, contractor, task order, match, federal $) + period totals; **PDF** includes an official cover page (Ferry County / CWDG / billing period / federal total / prepared & reviewed by).
- `GET /compliance/reimbursement-package?period_start=…&period_end=…`
- `GET /compliance/grant-progress`
- Cadence lives in `reporting_obligations` — load **Notice of Award** / NOFO deadlines there.

## SENTINEL (corridor risk convergence)

Background intelligence: **atmosphere** (NOAA `api.weather.gov` hourly + active alerts), **canopy** (roads / treatments / waypoints heuristics; LANDFIRE-style static mix per segment), **ground** (drought/slope stress proxy; optional SNOTEL probe — degrades safely if upstream fails). Latest scan rows live in **`sentinel_scans`** / **`sentinel_road_risks`** (`alembic upgrade head`).

- `GET /sentinel/status` — last scan metadata, Red Flag flag, top 3 corridors
- `GET /sentinel/risks?limit=&level=` — rows from the latest completed scan
- `GET /sentinel/risks/{road_id}` — risk row + fresh stream snapshots for breakdown
- `POST /sentinel/scan` — run a full scan synchronously (needs open network for NOAA)
- `GET /sentinel/history/{road_id}` — recent scan history for that road

**Ops env:** `SENTINEL_SCHEDULER_ENABLED=true` (and ensure `TESTING=false`) to start APScheduler: fire-season cron (May–Oct, 4×/day) + hourly Red Flag ping. Default is **off** so CI/laptops do not background-scan.

## Offline sync (idempotent — **applies treatments**)

`POST /sync/operations` runs the **same treatment create** as `POST /treatments/roads/{id}` when `entity_type` is `treatment` and `operation` is `create`. The payload is flat JSON: **all treatment fields** plus **`road_id`**. Use a stable **`client_operation_id`** (UUID) per offline action; retries must reuse the same id and identical JSON or the server returns **409** if the payload hash differs.

```http
POST /sync/operations
X-Actor: david
Content-Type: application/json

{
  "client_operation_id": "550e8400-e29b-41d4-a716-446655440000",
  "entity_type": "treatment",
  "operation": "create",
  "payload": {
    "road_id": 1,
    "treatment_date": "2026-04-01",
    "miles_treated": 0.25,
    "treatment_type": "brush_clear",
    "match_documented": true,
    "amount_federal": 75,
    "amount_match": 25,
    "davis_bacon_certified": true,
    "contractor_invoice_amount": 100
  }
}
```

Response includes `result.treatment_id` on first apply; duplicate replays return the same `result` without inserting another row.

## Security notes (red-team)

- KML XML is parsed with **`defusedxml`**; uncompressed `doc.kml` is capped (**60 MB**); uploads capped (**30 MB** archive).
- See [`tests/test_redteam.py`](tests/test_redteam.py).

## Tests

```bash
make test
pytest tests/ -v -m integration   # needs PostGIS
```

**CI** (GitHub Actions): on changes under `ferry_county/`, runs **backend pytest** (excluding integration) and **frontend Vitest + Playwright** (see [`.github/workflows/ferry-county-ci.yml`](../.github/workflows/ferry-county-ci.yml)). Local quick gate: `make ci`.

**Offline ordering:** the client sorts the outbox as **track → treatment → waypoint** before each flush so track rows exist before treatments that reference them. Treatments can use **`client_track_operation_id`** (the UUID used when the track was queued) instead of **`track_id`**; the server resolves it from **`sync_operations.result_json`** after the track sync commits. Prefer uploading/linking the real **`track_id`** when online.

## Grant language

CWDG-style programs: quarterly financial reporting, annual performance **with spatial**, final closeout. Your **award** controls exact dates — mirror them in `reporting_obligations`.
