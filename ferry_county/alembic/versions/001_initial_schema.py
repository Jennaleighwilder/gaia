"""initial schema — PostGIS + CWDG compliance core

Revision ID: 001_initial
Revises:
Create Date: 2026-04-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

from backend.database import Base

# Import all models so metadata is complete
from backend.models import (  # noqa: F401
    AnnualPerformanceReport,
    Attachment,
    AuditLog,
    QuarterlyFinancialReport,
    ReportingObligation,
    ReconciliationLog,
    Road,
    SyncOperation,
    Track,
    Treatment,
    Waypoint,
)

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    bind.commit()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
