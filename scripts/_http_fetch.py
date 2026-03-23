"""Shared HTTP fetcher with headers to avoid 403 (User-Agent blocking)."""
from __future__ import annotations

from urllib.request import Request, urlopen

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def fetch_bytes(url: str, timeout: int = 90) -> bytes:
    """Fetch URL with browser-like headers. Raises on error."""
    req = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "*/*"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()
