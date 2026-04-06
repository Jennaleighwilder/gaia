"""WSGI entry for gunicorn on Railway/Render: gunicorn runtime.dashboard.wsgi:app"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.config.env_loader import load_local_env

# Picks up .env.local / .env when present (local). Railway/Render inject os.environ in the dashboard.
load_local_env()

from runtime.dashboard.app import app
from runtime.dashboard.live_data_loop import start_live_data_refresh_thread

start_live_data_refresh_thread()

__all__ = ["app"]
