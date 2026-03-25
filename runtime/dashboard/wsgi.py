"""WSGI entry for gunicorn on Railway: gunicorn runtime.dashboard.wsgi:app"""

from runtime.dashboard.app import app

__all__ = ["app"]
