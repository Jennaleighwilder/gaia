from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_PATHS = (ROOT / ".env.local", ROOT / ".env")


def load_local_env(paths: tuple[Path, ...] = DEFAULT_ENV_PATHS, override: bool = False) -> None:
    """Load simple KEY=VALUE pairs from local env files without extra dependencies."""
    for path in paths:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if not key:
                continue
            if override or key not in os.environ:
                os.environ[key] = value
