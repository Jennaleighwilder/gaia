"""WSGI entry for gunicorn on Railway/Render: gunicorn runtime.dashboard.wsgi:app"""

from runtime.dashboard.app import app
from runtime.dashboard.live_data_loop import start_live_data_refresh_thread

start_live_data_refresh_thread()

__all__ = ["app"]
