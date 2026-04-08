"""sync_operations.result_json — idempotent replay payload

Revision ID: 002_result
Revises: 001_initial
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB

revision = "002_result"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    cols = [c["name"] for c in insp.get_columns("sync_operations")]
    if "result_json" not in cols:
        op.add_column("sync_operations", sa.Column("result_json", JSONB(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    cols = [c["name"] for c in insp.get_columns("sync_operations")]
    if "result_json" in cols:
        op.drop_column("sync_operations", "result_json")
