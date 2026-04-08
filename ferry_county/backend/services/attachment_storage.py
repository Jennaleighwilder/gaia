from __future__ import annotations

import hashlib
import re
from pathlib import Path

from backend.config import get_settings

_FILENAME_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def _storage_root() -> Path:
    p = Path(get_settings().attachment_storage_dir).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_uploaded_file(data: bytes, original_name: str) -> tuple[str, str]:
    """
    Write bytes to content-addressed path. Returns (sha256_hex, storage_uri).
    storage_uri format: local:{sha[:2]}/{sha}
    """
    h = hashlib.sha256(data).hexdigest()
    root = _storage_root()
    rel = f"{h[:2]}/{h}"
    dest = root / h[:2] / h
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_bytes(data)
    _ = original_name  # reserved for future sidecar metadata
    return h, f"local:{rel}"


def blob_path_for_uri(storage_uri: str) -> Path | None:
    if not storage_uri.startswith("local:"):
        return None
    rel = storage_uri.removeprefix("local:")
    return _storage_root() / rel


def safe_original_filename(name: str, max_len: int = 200) -> str:
    base = Path(name).name
    base = _FILENAME_SAFE.sub("_", base)[:max_len]
    return base or "upload.bin"
