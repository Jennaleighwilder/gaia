from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.config import get_settings

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            future=True,
        )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine, future=True)
    return _engine


def get_session_factory():
    get_engine()
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_engine() -> None:
    """Test helper: clear cached engine when DATABASE_URL changes."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def ensure_postgis(db: Session) -> None:
    db.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    db.commit()
