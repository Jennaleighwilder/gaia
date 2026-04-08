# Technical Support & Maintenance Playbook

**Audience:** IT help desk, designated “system owner,” vendor escalation  
**Style:** Practical steps first, theory second

---

## 1. Severity levels (suggested)

| Level | Example | Target response |
|-------|---------|-----------------|
| **S1** | Public portal down during evacuation; DB unreachable | Immediate |
| **S2** | Field app offline for active crew | Same business day |
| **S3** | Single workstation installer failure | 2 business days |
| **S4** | Cosmetic / training questions | Next clinic |

---

## 2. First-response checklist (any report)

1. **What** is failing — Field app, public URL, database, or network?  
2. **Who** — one user or everyone?  
3. **When** did it last work?  
4. **Screenshots** or exact error text (splash screen, browser, Windows Event Viewer for Postgres).

---

## 3. Common issues

### 3.1 “Application won’t start” (Electron)

- Confirm **PostgreSQL** Windows service is **Running**.  
- Confirm **first-run wizard** credentials — test with `psql` or pgAdmin from the same machine.  
- Verify **`ferry_backend.exe`** exists under the app’s resources folder (repair install if missing).

### 3.2 Map is blank

- Check **internet** for raster tiles (MapLibre basemap).  
- Check **API** reachable: same origin `/api` or configured **`VITE_API_BASE`**.  
- Check browser **console** for CORS errors — add origin to **`CORS_ORIGINS`**.

### 3.3 “Sync pending” never clears (Field app)

- Device **online**?  
- **Flush** button — any error message?  
- Server **`POST /sync/operations`** — review API logs for **409** (idempotent conflict) or **400** validation.

### 3.4 Public portal shows stale data

- Public endpoints are **cached** in places (weather ~15 minutes).  
- **Evacuation zones** — confirm EOC posted updates via **`/emergency/*`** with correct **`X-Actor`**.  
- Browser **hard refresh**; verify CDN/proxy not caching JSON aggressively.

### 3.5 SENTINEL scan empty or slow

- **NOAA** or network timeouts — optional tokens missing degrade gracefully.  
- **`POST /sentinel/scan`** — check API logs; ensure **roads exist** (KMZ imported) and grant roads have expected flags.

---

## 4. Maintenance calendar (suggested)

| Frequency | Task |
|-----------|------|
| **Daily** (automated) | DB backup success alert |
| **Weekly** | Disk space on DB and attachment volume |
| **Monthly** | Review failed sync operations (if metrics available); OS patches |
| **Quarterly** | Restore drill; rotate secrets if policy requires |
| **Annually** | Full DR test; training refresher for EOC |

---

## 5. Escalation to developer / vendor

Include in every ticket:

- **Version** (installer filename or `git` commit if dev build).  
- **OS** version.  
- **PostgreSQL** version.  
- **Redacted** `DATABASE_URL` host only (not password).  
- **Steps to reproduce** and **logs** (API stderr, Alembic output from splash).

---

## 6. After-hours emergency (EOC)

- **Public portal** is read-only — if the **hosting** stack fails, switch to **alternate communications** (reverse 911, radio) per county plan — this system is **supplemental**.  
- **Emergency writes** must work from **trusted** networks; if VPN is down, use contingency procedures documented by the county.

---

*Maintain this playbook with dates and names when procedures change.*
