# FERRY COUNTY — Complete Handoff Package

This folder is a **self-contained delivery bundle** intended for USB flash drive, secure file share, or air-gapped handoff. It contains everything a county IT lead, program administrator, and field staff need to **understand**, **deploy**, **operate**, and **maintain** the system—without requiring access to the developer’s machine.

> **Folder name in the repository:** `Ferry_County_Complete_Package` (avoids collision with the code directory `ferry_county/` on case-insensitive disks). **On your flash drive, rename this folder to `FERRY COUNTY` or `FERRY_COUNTY`** if you want the exact title for recipients.

---

## What you have in this folder

| Document | Purpose |
|----------|---------|
| **README.md** (this file) | Orientation and reading order |
| **SPECIFICATION.md** | System specification sheet — scope, components, interfaces |
| **DEPLOYMENT.md** | Step-by-step deployment — Windows installer, database, optional web stack |
| **ADMINISTRATOR_GUIDE.md** | Access model, environment variables, backups, updates |
| **SUPPORT_AND_MAINTENANCE.md** | Tech support playbooks, upkeep schedule, escalation |
| **MANUAL.html** | Full operator & administrator manual (open in a browser; print to PDF — see **HOW_TO_PRINT_PDF.md**) |
| **HOW_TO_PRINT_PDF.md** | Create a polished PDF from the HTML manual |
| **PACKAGE_CHECKLIST.md** | What to place on the USB beside this folder before mailing |
| **FERRY_COUNTY_GAUNTLET.md** | Red-team / full-stack verification (12 sections, curl + DB + package integrity) |
| **ROAD_SEARCH_CURSOR_PROMPT.md** | Spec for live road search (also implemented in app — see `GET /roads/search`) |

---

## Integrity check (repo health)

- **`ferry_county/README.md`** must begin with the developer title **Ferry County — CWDG field & compliance** — not “Complete Handoff Package.” If a handoff README overwrote it, restore from git history.
- This **`Ferry_County_Complete_Package/`** folder is the canonical **documentation** bundle; application code stays under **`ferry_county/`**.

---

## Recommended reading order

1. **SPECIFICATION.md** — Know what was built and what it connects to.  
2. **DEPLOYMENT.md** — Install PostgreSQL (if needed), run the Windows installer, import roads.  
3. **MANUAL.html** — Day-to-day use for field, EOC, and public-facing features.  
4. **ADMINISTRATOR_GUIDE.md** — Ongoing configuration and data protection.  
5. **SUPPORT_AND_MAINTENANCE.md** — When something breaks or a new machine is added.  
6. **PACKAGE_CHECKLIST.md** — Before you seal the envelope or ship the drive.  
7. **FERRY_COUNTY_GAUNTLET.md** — Before go-live or after major releases (run against staging).  
8. **ROAD_SEARCH_CURSOR_PROMPT.md** — Reference for the live “find road on map” feature.

---

## Software deliverable (not stored in git)

The **Windows NSIS installer** (`.exe`) is produced by **GitHub Actions** in the `gaia` repository (**Build Windows installer** workflow). Download the artifact from the **green** run and place it **beside this folder** on the flash drive:

- Suggested flash drive layout:
  - **`FERRY COUNTY/`** (this folder, renamed from `Ferry_County_Complete_Package`)  
  - **`Ferry County Field System-Setup-x.x.x.exe`** — installer from CI artifacts  
  - Optional: **`FerryCounty_Complete_Roads_v2.kmz`** — county road inventory (if your license allows redistribution)

---

## Support contacts (fill in before distribution)

| Role | Name | Phone | Email |
|------|------|-------|-------|
| Primary IT / admin | | | |
| Vendor / developer escalation | | | |
| County emergency coordinator | | | |

---

## Version & source

- Documentation package for **Ferry County CWDG Field System** — application source lives in repository path **`ferry_county/`**, Electron desktop shell, optional Docker/nginx deployment.  
- Technical contract: **`ferry_county/docs/SPEC.md`** (with repository access).

## About **MANUAL.html** design

The manual uses a restrained **Southern Gothic** visual tone—wine and forest greens on aged paper, traditional serif titles—while body text stays **sans-serif** for readability. Open in any browser; print to PDF for a bound copy (**HOW_TO_PRINT_PDF.md**).

---

*This package is designed to stand alone. If the recipient has only this folder and the installer, they should still be able to deploy and run the system using these documents.*
