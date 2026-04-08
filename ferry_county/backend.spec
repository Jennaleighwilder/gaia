# PyInstaller spec — produces ferry_county/electron/resources/ferry_backend/ (onedir).
# Run from ferry_county/: pyinstaller backend.spec --distpath electron/resources --clean

block_cipher = None

a = Analysis(
    ["backend_runner.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("backend", "backend"),
        ("alembic", "alembic"),
        ("alembic.ini", "."),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "geoalchemy2.types",
        "geoalchemy2.functions",
        "shapely",
        "shapely.geometry",
        "reportlab",
        "reportlab.lib",
        "reportlab.platypus",
        "psycopg2",
        "alembic",
        "apscheduler",
        "apscheduler.schedulers.asyncio",
        "pydantic_settings",
        "multipart",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ferry_backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ferry_backend",
)
