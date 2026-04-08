# Ferry County Field System — Gauntlet (Red-Team / Full-Stack Verification)

**Purpose:** Aggressive, layer-by-layer verification before production handoff or after major changes.  
**Audience:** Cursor, CI maintainers, county IT (sections can be run manually).  
**Safety:** Run against **non-production** first. Some steps are destructive if pointed at prod.

---

## How to use this document

- Each section has **commands** (bash / `curl` / `pytest`) and **pass criteria**.  
- Mark **SKIP** if your environment lacks optional assets (e.g. Excel workbook).  
- **Do not** run load tests against production without approval.

---

## 1. Database integrity

| Step | Command / action | Pass |
|------|------------------|------|
| 1.1 | `cd ferry_county && alembic current` | Shows latest revision (e.g. `005_waypoint_infra` or newer). |
| 1.2 | `alembic upgrade head` on empty schema → no error. | All migrations apply. |
| 1.3 | Postgres: `SELECT PostGIS_Version();` | PostGIS present. |
| 1.4 | `SELECT COUNT(*) FROM roads WHERE deleted_at IS NULL;` after KMZ import | Matches expected county count (e.g. **5339** for `FerryCounty_Complete_Roads_v2.kmz`). |
| 1.5 | Geometry validity sample: `SELECT COUNT(*) FROM roads WHERE NOT ST_IsValid(geometry);` | **0** invalid. |
| 1.6 | `SELECT DISTINCT district FROM roads WHERE district IS NOT NULL LIMIT 20;` | Reasonable district values (or document if NULL-only). |

**Red-team:** Attempt `alembic downgrade -1` on a **throwaway** DB only — confirm downgrade SQL matches expectations.

---

## 2. Backend endpoints (status codes)

With API base `http://127.0.0.1:8090` (adjust port). Use `-i` to see status lines.

| Endpoint | Method | Auth / headers | Expected |
|----------|--------|----------------|----------|
| `/health` | GET | — | **200** |
| `/roads` | GET | — | **200**, JSON `items` array |
| `/roads/geojson` | GET | — | **200**, `FeatureCollection` |
| `/roads/search?q=test` | GET | — | **200** or **400** if `q` empty (see implementation) |
| `/roads/search?q=` | GET | — | **400** if validation rejects empty query |
| `/public/status` | GET | — | **200** |
| `/public/weather` | GET | — | **200** |
| `/public/evacuation-zones` | GET | — | **200** GeoJSON |
| `/sentinel/status` | GET | — | **200** |
| `/sentinel/scan` | POST | — | **200** |
| `/compliance/match-ratio` | GET | — | **200** |
| `/emergency/roads-search?q=x` | GET | `X-Actor: test` optional | **200** |
| `/gis/security-config` | GET | — | **200** |
| `/sync/operations` | POST | malformed JSON body | **422** validation |

**Red-team:** `GET /roads/by-source/does-not-exist` → **404**.  
**Red-team:** `POST /gis/import-kmz` with path import disabled → **403** (default).

---

## 3. Road search (field feature)

| Step | Action | Pass |
|------|--------|------|
| 3.1 | `GET /roads/search?q=Main` | **200**, `items.length <= 10`, each item has `id`, `road_name`, `center` or `lon`/`lat` per spec |
| 3.2 | `GET /roads/search?q=` | **400** |
| 3.3 | `GET /roads/search?q=zzzznomatch12345` | **200**, `items: []` |
| 3.4 | SQL injection probe: `q=%25%27%20OR%201%3D1--` | Returns normal ILIKE results or empty — **no** syntax error, **no** elevated row count explosion |

**Frontend (manual):** Type partial name → results list → pick → map **flies** to road, **yellow** highlight visible.

---

## 4. Offline sync queue

| Step | Action | Pass |
|------|--------|------|
| 4.1 | `useOfflineSync` flush: **422** from server removes bad row (skip). | Documented in `useOfflineSync.js` |
| 4.2 | Non-422 error stops flush loop; item remains for retry. | Matches implementation |
| 4.3 | `POST /sync/operations` duplicate `client_operation_id` | **200** duplicate path, no double insert |

**Note:** **503** retry semantics — confirm whether API returns 503 under stress; client should leave queue intact.

---

## 5. Electron / Windows bundle (when available)

| Step | Action | Pass |
|------|--------|------|
| 5.1 | Installer launches splash → main window. | No crash |
| 5.2 | First-run wizard accepts DB URL. | Alembic runs or shows actionable error |
| 5.3 | `resources/ferry_backend/ferry_backend.exe` exists next to app. | Present |

---

## 6. KMZ integrity

| Step | Action | Pass |
|------|--------|------|
| 6.1 | File hash recorded (SHA-256) for `FerryCounty_Complete_Roads_v2.kmz` | Matches known good |
| 6.2 | Import → `parsed_in_file` matches `inserted` + existing (idempotent skip) | Stats logged |
| 6.3 | Spot-check: LAPR folder segments ≈ **396** grant segments (per spec) | Document variance |

---

## 7. Excel / external workbook (optional)

If county maintains **Excel** with ~**327** rows (or similar):

| Step | Action | Pass |
|------|--------|------|
| 7.1 | Row count matches export from system or documented delta | Recorded |
| 7.2 | Spot-check 3 random road names vs DB `road_name` | Match |

**SKIP** if no workbook.

---

## 8. Handoff package integrity

| Step | Action | Pass |
|------|--------|------|
| 8.1 | `Ferry_County_Complete_Package/README.md` exists | Yes |
| 8.2 | `ferry_county/README.md` first line contains **CWDG field & compliance** (dev README) — **not** “Complete Handoff Package” | Prevents accidental overwrite |
| 8.3 | `MANUAL.html`, `DEPLOYMENT.md`, `SPECIFICATION.md` present under package | Yes |

---

## 9. SQL injection & input fuzzing

| Payload | Target | Pass |
|---------|--------|------|
| `q='; DROP TABLE roads;--` | `/roads/search` | No 500; table still exists |
| Long `q` (2000 chars) | `/roads/search` | **400** or **422** or truncated safely — not 500 |

---

## 10. Concurrency (light)

```bash
for i in {1..20}; do curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8090/public/status" & done; wait
```

**Pass:** All **200**, no connection refused from single worker uvicorn (some 502 acceptable behind proxy only).

---

## 11. Performance baselines (informal)

| Endpoint | Rough budget (local SSD, warm DB) |
|----------|-----------------------------------|
| `GET /roads/geojson` | < 5s for full county |
| `GET /public/status` | < 500ms |
| `POST /sentinel/scan` | Depends on road count; note wall time |

Record numbers in your runbook.

---

## 12. Full integration smoke (top to bottom)

1. `make db-up` → `alembic upgrade head`  
2. Import KMZ  
3. Start API + frontend (`npm run dev` with proxy)  
4. Open Field app → map renders  
5. **Road search** → fly + highlight  
6. Log dummy treatment (or vertical slice script)  
7. `POST /sentinel/scan` → `road_count` > 0 when grant roads exist  
8. Open `/public` → status loads  

**Pass:** No uncaught console errors on critical path.

---

## Automated test mapping (pytest / Playwright)

- `ferry_county/tests/` — run `pytest tests/ -m "not integration"` in CI.  
- Add `tests/test_roads_search.py` when `/roads/search` lands.  
- Frontend e2e: extend mocked routes for `/roads/search`.

---

*Revise this gauntlet when new endpoints or threats are identified.*
