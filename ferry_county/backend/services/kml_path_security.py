from __future__ import annotations

import os
from pathlib import Path

from backend.config import get_settings, kmz_path_allow_prefix_list


class KmzPathImportNotAllowed(Exception):
    pass


class KmzPathNotAllowed(Exception):
    pass


def resolve_and_validate_kmz_path(path: str) -> str:
    """
    Server-side path imports are disabled by default (set allow_kmz_path_import).
    If kmz_path_allow_prefixes is non-empty, resolved path must sit under one prefix.
    """
    settings = get_settings()
    if not settings.allow_kmz_path_import:
        raise KmzPathImportNotAllowed(
            "Path-based KMZ import is disabled. Use POST /gis/import-kmz-upload "
            "or set ALLOW_KMZ_PATH_IMPORT=true for trusted automation only."
        )
    rpath = os.path.realpath(path)
    if not os.path.isfile(rpath):
        raise FileNotFoundError(rpath)
    prefixes = kmz_path_allow_prefix_list()
    if not prefixes:
        return rpath
    rp = Path(rpath).resolve()
    for p in prefixes:
        try:
            base = Path(p).expanduser().resolve()
            rp.relative_to(base)
            return rpath
        except ValueError:
            continue
    raise KmzPathNotAllowed(f"KMZ path must be under one of: {prefixes}")
