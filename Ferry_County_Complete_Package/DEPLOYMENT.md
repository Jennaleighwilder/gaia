# Ferry County Field System — Deployment Guide

**Audience:** County IT, installer technician  
**Time:** First machine 1–2 hours; additional machines faster  
**Prerequisites:** Windows 10/11 64-bit, administrator rights for PostgreSQL install, ~10 GB free disk

---

## Part A — Windows response-center PC (Electron installer path)

This is the path described in **`ferry_county/electron/setup/DEPLOYMENT_GUIDE.md`** in the source repository. This document consolidates that flow for handoff.

### A1. PostgreSQL (once per machine)

1. Obtain **`install_postgres.ps1`** from the Electron `setup` folder inside the repository (or from your vendor’s package).  
2. Edit the script: set **`$superPassword`** and **`$ferryPassword`** to **strong, unique** values. Record them in your **password vault** — not on sticky notes.  
3. Run **PowerShell as Administrator** → execute the script.  
4. Confirm Windows service **postgresql-16** (or your installed version) is **Running**.  
5. Note the **connection string** printed for SQLAlchemy, e.g.  
   `postgresql+psycopg2://ferry:YOUR_PASSWORD@127.0.0.1:5432/ferry_county`

### A2. Ferry County Field System installer

1. Obtain **`Ferry County Field System-Setup-<version>.exe`** from **GitHub Actions** artifacts (green build on `main`) or your release channel.  
2. Run the installer as a user allowed to install desktop software.  
3. Launch the application. Complete the **first-run wizard** with:
   - Host: `127.0.0.1` (same PC) or your DB host  
   - Port: `5432` (or as configured)  
   - Database name: as created by the script (e.g. `ferry_county`)  
   - User / password: **`ferry`** user from A1  

4. If migrations fail, the splash screen shows **Alembic** output — fix connectivity, then **Retry**.  
5. The bundled backend runs **`alembic upgrade head`** before serving the API when the packaged runner is configured to do so.

### A3. Road data (KMZ)

1. Obtain **`FerryCounty_Complete_Roads_v2.kmz`** (or your current county export).  
2. **Preferred:** use **`POST /gis/import-kmz-upload`** (multipart file) from a trusted admin machine with the API running — avoids server filesystem paths.  
3. **Alternative (automation only):** path-based import with `ALLOW_KMZ_PATH_IMPORT` — see technical spec; keep off in production unless jailed paths are configured.

**Python one-liner (maintenance machine with repo clone):**

```bash
cd ferry_county
export DATABASE_URL="postgresql+psycopg2://ferry:PASSWORD@127.0.0.1:5432/ferry_county"
.venv/bin/python -c "
from backend.database import get_session_factory
from backend.services.seed_kmz import import_kmz_file
db = get_session_factory()()
try:
    print(import_kmz_file(db, r'C:\\path\\to\\FerryCounty_Complete_Roads_v2.kmz', actor='seed'))
finally:
    db.close()
"
```

### A4. Verify

- Open the Field app — map should show roads after geojson loads.  
- `GET http://127.0.0.1:<api_port>/health` (or app-configured port) should return healthy.  
- Run **SENTINEL** scan from the UI or `POST /sentinel/scan`.

---

## Part B — Optional: Docker / Linux server (nginx + API + SPA)

For a **central server** instead of per-PC API:

1. Install **Docker** and **Docker Compose** on the server.  
2. From the **`ferry_county`** directory in the repo:  
   - Copy **`.env.example`** → **`.env`**; set **`DATABASE_URL`**, **`CORS_ORIGINS`** (your real UI origins).  
   - `make db-up` or use hosted PostGIS.  
   - `docker compose --profile stack up` (see **`ferry_county/README.md`**).  
3. Terminate TLS at **nginx** or a cloud load balancer; do not expose Postgres to the public internet.

---

## Part C — Public portal origin

Residents use **`/public`** on the SPA (e.g. `https://your-county.gov/cwdg/public`). Ensure:

- **HTTPS** in production.  
- **CORS** includes the static origin serving the SPA.  
- **Rate limiting** on unauthenticated public routes at the edge.  
- **Emergency writes** (`/emergency/*`) restricted to trusted networks or VPN.

---

## Part D — Rebuilding the Windows installer (developers only)

- **PyInstaller** output is **OS-specific**. The **`.exe`** artifact must come from **Windows** CI or a Windows build host.  
- From **`ferry_county/electron`** on Windows, with Python deps installed:  
  `npm ci` → `npm run dist:win`  
- Confirm **`electron/resources/ferry_backend/`** contains the backend bundle before packaging.

---

## Checklist before “go-live”

| Step | Done |
|------|------|
| Postgres passwords rotated from defaults | ☐ |
| TLS certificate for public URL | ☐ |
| `CORS_ORIGINS` matches production UI | ☐ |
| KMZ imported; road count sanity-checked | ☐ |
| Backup job scheduled (see ADMINISTRATOR_GUIDE) | ☐ |
| EOC trained on emergency panel + public URL | ☐ |

---

*Deployment details may be updated in the repository; this file is a handoff snapshot.*
