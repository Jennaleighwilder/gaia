from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://ferry:ferry@127.0.0.1:5434/ferry"
    ferry_kmz_path: str | None = None
    match_ratio_required: float = 0.25
    davis_bacon_threshold_usd: float = 2000.0
    # Security: JSON body /gis/import-kmz with arbitrary filesystem paths is dangerous.
    # Prefer POST /gis/import-kmz-upload. Enable path import only for local automation.
    allow_kmz_path_import: bool = False
    # Comma-separated absolute path prefixes; if set, path imports must match one prefix after realpath.
    kmz_path_allow_prefixes: str = ""
    # Comma-separated origins for Phase 2 Field PWA (Vite dev, production CDN, etc.)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080"
    # Local disk blob store for attachment uploads (no S3 required).
    attachment_storage_dir: str = "data/ferry_attachments"
    max_attachment_bytes: int = 30 * 1024 * 1024  # 30 MB
    # SENTINEL convergence (suppress network jobs in CI / unit runs)
    testing: bool = False
    sentinel_http_timeout_s: float = 20.0
    sentinel_scheduler_enabled: bool = False
    # NOAA Climate Data Online (Palmer / long-lead); optional — degrades without token
    noaa_cdo_token: str = ""
    # GAIA atmospheric bundle (Railway); optional — NOAA used when unavailable
    gaia_weather_bundle_url: str = "https://web-production-ce417.up.railway.app/api/bundle"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()


def kmz_path_allow_prefix_list() -> list[str]:
    s = get_settings().kmz_path_allow_prefixes.strip()
    if not s:
        return []
    return [p.strip() for p in s.split(",") if p.strip()]
