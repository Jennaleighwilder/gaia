# Ferry County CWDG — system spec (Phase 1, hardened)

This document is the **operational contract** for the backend in `ferry_county/`. It supersedes informal “skeleton only” prompts: **security defaults**, **KMZ identity**, **compliance math**, and **reporting hooks** are **non-optional**.

## 1. Identity & inventory

- **Primary key for roads**: `roads.source_feature_id` — deterministic `fc_` + SHA-256 of `(kml_folder_path | road_name | geometry_wkt)`.
- **Never** use road name alone as a key (duplicate street names across segments/districts are expected).
- **KMZ source**: `FerryCounty_Complete_Roads_v2.kmz` validates to **5339** line features, **396** in the LAPR folder (as parsed by this codebase).
- **Field map layer**: `GET /roads/geojson` — same road geometries as GIS export, plus **`treatment_status`** and **`is_grant_road`** (true when CEMP miles > 0) for client styling (grant-untreated vs non-grant, partial, complete).

## 2. Security (red-team defaults)

- **Preferred import**: `POST /gis/import-kmz-upload` (multipart `.kmz`). No server filesystem read.
- **Path import** (`POST /gis/import-kmz` with JSON path): **disabled by default**. Enable only on trusted hosts:
  - `ALLOW_KMZ_PATH_IMPORT=true`
  - Optional jail: `KMZ_PATH_ALLOW_PREFIXES=/abs/dir1,/abs/dir2`
- **XML**: KML is parsed with **`defusedxml`** (mitigates XML bombs / XXE compared to naive `ElementTree`).
- **Size limits**:
  - Uncompressed `doc.kml` ≤ **60 MB** inside the ZIP.
  - Upload endpoint rejects archives **> 30 MB** (tune as needed).

## 3. Acreage

- Strip acres from centerline miles and **15 ft per side** (30 ft total width):
  - `acres = miles * 5280 * (2 * buffer_ft) / 43560`
- Default buffer **15 ft** (USDA-style corridor strip).

## 4. Compliance fields (treatments)

- **Match**: `match_documented`, `match_source`, `match_amount`, optional `amount_federal` / `amount_match` for ratio checks.
- **Davis-Bacon**: `davis_bacon_certified`, `davis_bacon_wage_rate`; **warning** if `contractor_invoice_amount` > threshold (default **$2000**) and not certified.
- **Submission**: `submitted_to_usda`, `submission_date` — extend with immutable snapshots before marking submitted.

### 4.1 Compliance HTTP (aggregates & exports)

- **`GET /compliance/match-ratio`** — Sums `amount_federal` on non-deleted treatments; sums `amount_match` where `match_documented` is true. **Match share** = match / (federal + match). **Compliant** when share ≥ `match_ratio_required` from config (default **0.25**). Response includes **ratio_percent** and **match_ratio_required_percent**.
- **`GET /compliance/export/geojson`** | **`GET /compliance/export/kmz`** — Treatments with `treatment_date` in **[period_start, period_end]** as GeoJSON FeatureCollection or KMZ (`doc.kml`). Geometry is the road’s **full** corridor **MultiLineString** (inventory geometry), not a per-mile clip — properties carry miles, acres, contractor, treatment ids.
- **`POST /compliance/quarterly-report`** — Creates a row in **`quarterly_financial_reports`**: federal + match cash + in-kind → **total_spend**, **match_ratio** = (cash + in-kind) / total_spend; **submitted** flag and optional **submitted_date** / **notes**.

## 5. Audit & evidence

- `audit_log` on treatment create (extend to updates/submissions).
- `attachments`: SHA-256 + `storage_uri` + foreign keys — **metadata is not optional** for reimbursement defense.
- **No hard deletes** on grant-bearing rows — use `deleted_at` when soft-delete endpoints exist.

## 6. Sync (field / offline)

- `POST /sync/operations` is **idempotent** on `client_operation_id` (UUID string, 32–36 chars).
- **Payload hash** = SHA-256 of canonical JSON (`sort_keys=True`). Same id + **different** payload → **409 Conflict** (prevents silent overwrite).
- **Supported operations** (extend as needed):
  - `entity_type`: `treatment`, `operation`: `create`
  - `payload` matches **`TreatmentSyncPayload`**: all `TreatmentCreate` fields plus **`road_id`** (integer), optional **`track_id`** linking field GPS evidence. Optional **`actor`** if `X-Actor` header is absent.
  - `entity_type`: `track`, `operation`: `create`
  - `payload` matches **`TrackSyncPayload`**: **`points`** (≥2 vertices with `lon`/`lat`, optional `accuracy_m`), optional **`road_id`**, optional **`start_time`** / **`end_time`** (ISO-8601). Stored as PostGIS **`LINESTRING`** + **`raw_gps_log`** JSON.
  - `entity_type`: `waypoint`, `operation`: `create`
  - `payload` matches **`WaypointSyncPayload`**: **`lat`/`lon`**, optional **`road_id`**, material / **Buy America** fields (`buy_america_certified`, `material_cost`, `vendor`, etc.).
- **Treatment + track reference**: REST and sync accept optional **`track_id`** (server id) **or** **`client_track_operation_id`** (UUID of the track’s sync op). If the latter is used, **`create_treatment`** resolves the numeric **`track_id`** from **`sync_operations`** where **`result_json.entity == "track"`** — the track sync must be committed first (field client flush order: track before treatment).
- **Server behavior**:
  - On first success: runs the same `create_treatment` path as REST, stores **`result_json`** on `sync_operations` (e.g. `{"entity":"treatment","treatment_id":N,"road_id":M}`).
  - On replay: returns `status: duplicate` and the **same** `result` — **no second treatment row**.
  - **PostgreSQL**: `pg_advisory_xact_lock` on a key derived from `client_operation_id` prevents concurrent double-apply.
- Response shape: `{ "status": "applied"|"duplicate", "sync_operation_id", "payload_hash", "result": { ... } }`.

## 7. Reporting cadence

- Do **not** hardcode semi-annual vs annual in business logic.
- Use `reporting_obligations` + award PDF when available (NOFO pattern: quarterly financial via **`quarterly_financial_reports`** + **`POST /compliance/quarterly-report`**, annual performance + spatial via **§4.1** exports, final).

## 8. Runbook commands

```bash
make install
make db-up
export DATABASE_URL=postgresql+psycopg2://ferry:ferry@127.0.0.1:5434/ferry
make migrate
make test
export FERRY_KMZ=/absolute/path/to/FerryCounty_Complete_Roads_v2.kmz
make vertical-slice
```

## 9. Python version

- **3.11–3.13** supported for dependencies. **3.14** may fail on `pydantic-core` wheels — use 3.13 until upstream catches up.

## 10. Phase 2 — Field PWA (operator UI)

- **Purpose**: Map + GPS + treatment logging + **offline queue** (`IndexedDB`) that flushes to **`POST /sync/operations`** with the same idempotency rules as §6.
- **Waypoints**: Material / vendor / **Buy America** capture via **`POST /waypoints`** or sync **`waypoint`/`create`**.
- **Attachments**: **`POST /attachments/upload`** (multipart) stores blobs under **`ATTACHMENT_STORAGE_DIR`** (SHA-256 content addressing); **`GET /attachments/{id}/file`** serves bytes. Metadata-only **`POST /attachments`** remains for external **`storage_uri`** workflows.
- **API base**: In production, same-origin **`/api`** (nginx reverse-proxy to uvicorn). Dev: Vite proxies **`/api` → `127.0.0.1:8090`**.
- **CORS**: Server **`cors_origins`** (env **`CORS_ORIGINS`**) must list every browser origin that loads the SPA (Vite **5173**, Docker stack **8080**, production CDN).
- **Audit**: `POST /treatments/...` and **`POST /sync/operations`** both send **`X-Actor`** from the Field “Actor” field (header preferred; sync payload may carry `actor` if header absent).
- **Deploy**: `docker compose --profile stack` (see `README.md`) — **PostGIS** + **API** + **nginx** static SPA; **not** a substitute for TLS, secrets management, or hosted DB — those are environment-specific.
