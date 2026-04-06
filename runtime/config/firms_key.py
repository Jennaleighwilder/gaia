"""NASA FIRMS MAP_KEY resolution for GAIA.

`FIRMS_MAP_KEY` in the environment always wins. If unset (common when cloud
dashboard secrets were not added), we use the project-registered public API key
so fire ingest and cache fetches still work on Railway/Render without extra setup.
"""

from __future__ import annotations

import os

GAIA_FIRMS_MAP_KEY_FALLBACK = "0ee5bc57f83cb21a76a3250960c7806a"


def resolve_firms_map_key() -> str:
    env = os.environ.get("FIRMS_MAP_KEY", "").strip()
    return env or GAIA_FIRMS_MAP_KEY_FALLBACK


def firms_map_key_explicit_env() -> bool:
    return bool(os.environ.get("FIRMS_MAP_KEY", "").strip())
