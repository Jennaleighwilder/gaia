# Ferry County Field System — deployment (response center Windows PCs)

## What you are installing

- **PostgreSQL** (server): not bundled; install once per machine with the PowerShell script.
- **Ferry County Field System**: one **NSIS** installer built from this repo. It ships **Electron** plus a **PyInstaller** folder `ferry_backend` (FastAPI, uvicorn, SQLAlchemy/PostGIS drivers, ReportLab, APScheduler, Alembic assets). No Python runtime is required on the workstation.

## Prerequisites

- Windows 10 or 11, 64-bit  
- ~8 GB RAM, ~10 GB free disk (PostgreSQL + app + data growth)  
- Administrator rights for the PostgreSQL install step  
- Network for basemap tiles where used  

## Step 1 — PostgreSQL (once per machine, as Administrator)

1. Edit **`setup/install_postgres.ps1`**: set **`$superPassword`** and **`$ferryPassword`** to strong values; keep them for IT records.  
2. Right-click the script → **Run with PowerShell as Administrator**.  
3. When it finishes, note the printed **SQLAlchemy URL** (`postgresql+psycopg2://ferry:…@127.0.0.1:5432/ferry_county`).  

Confirm the **postgresql-16** Windows service is **Running**.

## Step 2 — Ferry County Field System installer

1. Run **`Ferry County Field System-Setup-<version>.exe`**.  
2. Complete the installer (one-click NSIS flow; shortcuts optional per your policy).  
3. On first launch, the **setup wizard** tests the database and saves credentials under the app user-data folder.  

If PostgreSQL is on the same PC, you can use host `127.0.0.1`, port `5432`, database `ferry_county`, user `ferry`, and the **ferry** password from Step 1.

## Step 3 — Database migrations (Alembic)

On each launch, the desktop app runs **`alembic upgrade head`** automatically (via the same **Python** stack in development and the **bundled `ferry_backend` executable** in production) before the API starts. If migrations fail, the splash screen shows **Alembic output** and a **Retry** button.

For manual runs or troubleshooting, you can still invoke Alembic from a dev tree:

```bash
cd ferry_county
export DATABASE_URL="postgresql+psycopg2://ferry:YOUR_PASSWORD@HOST:5432/ferry_county"
alembic upgrade head
```

## Step 4 — Initial GIS / grant data

Load county roads, LAPR corridors, and boundaries per your data-delivery process (not part of the generic installer).

## Troubleshooting

- **App window errors on start**: confirm PostgreSQL is running; verify host/port/database/user/password in the first-run wizard.  
- **“Could not start the application”**: confirm `resources/ferry_backend/ferry_backend.exe` exists next to the installed app (repair/reinstall if missing).  
- **Map tiles blank**: check outbound HTTPS from the machine.  

## Before handing Steve the installer (one rebuild step)

PyInstaller builds a **host-OS** binary. The bundled backend must include the current **`backend_runner.py`** (including the **`FERRY_ALEMBIC_UPGRADE`** Alembic path) inside **`ferry_backend.exe`**.

On a **Windows** machine with the **full Ferry County Python environment** (same venv or system install you use to run the FastAPI app and tests), from **`ferry_county/electron`**:

```powershell
npm install
npm run build:backend
```

Confirm **`ferry_county\electron\resources\ferry_backend\ferry_backend.exe`** exists and has a recent timestamp. Then build the NSIS installer (below). **Do not** ship an installer that was built only on macOS/Linux unless you have a separate verified Windows CI artifact—those hosts produce a non-Windows binary.

## Rebuilding the Windows installer (developers)

From **`ferry_county/electron`** on a **Windows** build host with **Python 3**, all backend dependencies, and **PyInstaller**:

```powershell
npm install
npm run dist:win
```

`npm run dist:win` runs **`build:backend`** first, then **`electron-builder`**. `build:backend` writes **`electron/resources/ferry_backend/`**; the installer packages it via **`extraResources`** into **`electron/dist/`**.
