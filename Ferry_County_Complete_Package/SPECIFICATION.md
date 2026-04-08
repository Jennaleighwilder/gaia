# Ferry County Field System — Specification Sheet

**Document type:** System specification (handoff)  
**Audience:** County IT, program administration, auditors  
**Companion:** Technical deep-dive in repository `ferry_county/docs/SPEC.md` (if source access is available)

---

## 1. Purpose

The **Ferry County Field System** supports **CWDG** (County Wide Development Grant) style operations: **road inventory**, **treatment logging**, **compliance evidence**, **spatial exports** for USDA reporting, **offline-capable field capture**, and **public safety communications** (evacuation zones, road closures, incidents) without requiring residents to log in.

---

## 2. Major components

| Component | Technology | Role |
|-----------|------------|------|
| **API** | Python **FastAPI**, **SQLAlchemy**, **PostGIS** | Authoritative data, compliance math, sync idempotency, GIS |
| **Database** | **PostgreSQL** + **PostGIS** | Roads, treatments, waypoints, tracks, attachments metadata, audit log, public portal tables, SENTINEL scan results |
| **Field UI** | **React**, **Vite**, **MapLibre GL** | Map, GPS, treatments, waypoints, offline queue, emergency panel, public map route |
| **Desktop shell** | **Electron** + **PyInstaller** backend bundle | Single installer for Windows response-center PCs; runs API locally |
| **Migrations** | **Alembic** | Schema upgrades (`001` … `005+`); applied on app start in packaged mode when configured |

---

## 3. Functional scope (high level)

- **Road inventory** from **KMZ** (`FerryCounty_Complete_Roads_v2.kmz` or equivalent); stable identity via `source_feature_id` (not road name alone).  
- **Treatments** with federal/match amounts, Davis-Bacon flags, documentation hooks.  
- **Waypoints** (material sites, infrastructure types, inspection fields).  
- **Tracks** (GPS line evidence) with optional link to treatments.  
- **Attachments** (local disk storage path; SHA-256 addressed).  
- **Offline sync** — `POST /sync/operations` with idempotent client operation IDs.  
- **Compliance** — match ratio, quarterly reports, GeoJSON/KMZ exports by date range.  
- **Public portal** — read-only GeoJSON/JSON: evacuation zones, closures, incidents, weather.  
- **Emergency admin** — trusted `X-Actor` header pattern for EOC writes (same as field app).  
- **SENTINEL** — corridor risk scanning with atmosphere/ground inputs and ranked roads.  
- **Weather** — GAIA bundle first, NOAA fallback, 15-minute cache.

---

## 4. Interfaces (summary)

| Interface | Auth | Notes |
|-----------|------|-------|
| Field SPA `/` | Browser session; **`X-Actor`** for audit | Served via nginx or Vite dev |
| Public `/public/*` | **None** | Designed for phones; rate-limit at gateway in production |
| Emergency `/emergency/*` | **Trust boundary** — `X-Actor` | Restrict source IPs / VPN in production |
| API `/api` prefix | CORS from configured origins | Production: TLS termination at reverse proxy |

---

## 5. Non-goals (explicit)

- **Not** a replacement for county-wide E911 or NWS alerting as sole systems.  
- **Not** guaranteed real-time sub-second evacuation (network and client refresh intervals apply).  
- **Not** including PostgreSQL inside the Electron installer — installed separately per **DEPLOYMENT.md**.

---

## 6. Data classification (recommended county policy)

| Data | Sensitivity |
|------|-------------|
| Treatment $, contractor, match | **Confidential** — restrict backup access |
| GPS tracks / waypoints | **Operational** — may include PII if labeled |
| Public portal feeds | **Public** — intentionally unauthenticated |

---

## 7. Version matrix (typical)

| Layer | Typical version |
|-------|-----------------|
| Python | 3.11–3.13 |
| PostgreSQL | 14–16 (Windows script targets 16 in bundled guide) |
| Node (build only) | 24 (CI) |

---

## 8. Acceptance criteria (handoff)

- [ ] Installer runs on a clean Windows 11 PC; first-run wizard connects to Postgres.  
- [ ] KMZ import completes; `GET /roads/geojson` returns county features.  
- [ ] Field app loads map; treatment can be saved online.  
- [ ] `POST /sentinel/scan` completes; risks visible in UI or API.  
- [ ] Public status JSON returns from `/public/status` without auth.  
- [ ] Backups and restore path documented and tested once.

---

*This specification is a summary. Operational security, network topology, and county-specific policies belong in your IT runbooks.*
