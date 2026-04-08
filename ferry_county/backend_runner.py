"""
Entry point for PyInstaller-bundled Ferry County FastAPI backend.
- Normal: uvicorn backend.main:app
- FERRY_ALEMBIC_UPGRADE=1: alembic upgrade head (same exe / env as backend)
"""
from __future__ import annotations

import os
import sys


def _ensure_bundle_path() -> None:
    if getattr(sys, "frozen", False):
        bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        sys.path.insert(0, bundle_dir)
        os.chdir(bundle_dir)
    else:
        root = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, root)
        os.chdir(root)


def _run_alembic_upgrade() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    _ensure_bundle_path()

    if os.environ.get("FERRY_ALEMBIC_UPGRADE") == "1":
        try:
            _run_alembic_upgrade()
        except SystemExit as e:
            code = e.code
            if code is None:
                sys.exit(0)
            if isinstance(code, int):
                sys.exit(code)
            sys.exit(1)
        except Exception:
            import traceback

            traceback.print_exc(file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    import uvicorn

    port = int(os.environ.get("FERRY_PORT", "8765"))
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
