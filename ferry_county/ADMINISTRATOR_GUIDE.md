# Administrator Guide — Access, Configuration, Backups, Updates

**Audience:** County IT, designated system administrator  
**Scope:** What “full admin access” means in this system and how to protect it

---

## 1. What “admin access” means here

This application does **not** ship with a separate database super-user account inside the UI for county staff. Administrative control is exercised through:

| Mechanism | What it controls |
|-----------|------------------|
| **PostgreSQL** roles (`postgres`, `ferry`, backups) | Who can read/write raw data, run restores |
| **Windows / server OS** | Who can read attachment folders, config files, installer |
| **Environment variables** (`.env`, service config) | API behavior: CORS, paths, optional NOAA tokens |
| **`X-Actor` HTTP header** | Audit trail identity for API writes (field + emergency routes) |
| **Network policy** | Who can reach `/emergency/*` (must not be public internet without VPN) |

**There is no default “admin password” inside the React app** for county-wide settings — treat **`X-Actor`** and **database credentials** as privileged.

---

## 2. Environment variables (reference)

Set in **`.env`** next to the API or in your process manager / Windows service wrapper:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy URL to PostGIS database |
| `CORS_ORIGINS` | Comma-separated browser origins allowed for the Field SPA |
| `ATTACHMENT_STORAGE_DIR` | Directory for uploaded file blobs (must be on durable storage, backed up) |
| `ALLOW_KMZ_PATH_IMPORT` | `false` in production unless automation is jailed |
| `KMZ_PATH_ALLOW_PREFIXES` | Allowed absolute path prefixes when path import is on |
| `MATCH_RATIO_REQUIRED` | Program match share threshold (default 0.25) |
| `NOAA_CDO_TOKEN` | Optional — Palmer / long-lead drying features for SENTINEL |
| `GAIA_WEATHER_BUNDLE_URL` | Optional — atmospheric JSON; falls back to NOAA |

Never commit **`.env`** to git. Keep a **secure copy** in county IT vault.

---

## 3. Backups (minimum viable)

### 3.1 Database

- **Nightly logical backup** of the `ferry` (or `ferry_county`) database:  
  `pg_dump -Fc` (custom format) or `pg_dump` SQL.  
- Store **off-site** (encrypted).  
- **Test restore** quarterly on a non-production instance.

### 3.2 Attachments

- `ATTACHMENT_STORAGE_DIR` holds binary files referenced by SHA-256 in the DB.  
- Back up this directory **with** the DB; after restore, paths must match or update `storage_uri` consistently (avoid manual edits — prefer identical path layout).

### 3.3 Configuration

- Export **`.env`** (redacted in tickets), **nginx** site files, **TLS** cert renewal calendar.

---

## 4. Updates

### 4.1 Application

- **Desktop:** distribute new **`Ferry County Field System-Setup-x.x.x.exe`** from CI; uninstall/reinstall or in-place upgrade per vendor notes.  
- **Server / Docker:** pull new image, run migrations (`alembic upgrade head`) before cutting traffic.

### 4.2 Schema

- Alembic revisions live under **`ferry_county/alembic/versions/`**.  
- Always **backup before migrate** on production.

---

## 5. Audit and accountability

- **`audit_log`** records treatment-related events (extend as features grow).  
- **`X-Actor`** should be a **real county identifier** (e.g. `steve.eoc`, `david.field`) — not generic `admin`.  
- For public inquiries, correlate **public incident** rows with internal EOC logs outside this system if required by policy.

---

## 6. Hardening checklist (production)

- [ ] TLS everywhere for browser traffic  
- [ ] `/emergency/*` restricted to VPN or county IP range  
- [ ] Public routes rate-limited  
- [ ] Postgres not exposed to internet  
- [ ] Attachment directory permissions: service account only  
- [ ] Log rotation for API stdout / nginx access logs  

---

*For incident response (breach, lost laptop), start with database credential rotation and attachment directory access review.*
