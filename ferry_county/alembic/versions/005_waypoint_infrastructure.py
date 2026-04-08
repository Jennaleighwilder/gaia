"""waypoint infrastructure inventory fields

Revision ID: 005_waypoint_infra
Revises: 004_public_portal
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "005_waypoint_infra"
down_revision = "004_public_portal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    cols = {c["name"] for c in insp.get_columns("waypoints")} if "waypoints" in insp.get_table_names() else set()
    if "asset_condition" not in cols:
        op.add_column("waypoints", sa.Column("asset_condition", sa.String(20), nullable=True))
    if "asset_notes" not in cols:
        op.add_column("waypoints", sa.Column("asset_notes", sa.Text(), nullable=True))
    if "last_inspected" not in cols:
        op.add_column("waypoints", sa.Column("last_inspected", sa.Date(), nullable=True))
    if "inspected_by" not in cols:
        op.add_column("waypoints", sa.Column("inspected_by", sa.String(100), nullable=True))
    if "replacement_priority" not in cols:
        op.add_column("waypoints", sa.Column("replacement_priority", sa.String(10), nullable=True))


def downgrade() -> None:
    for col in (
        "replacement_priority",
        "inspected_by",
        "last_inspected",
        "asset_notes",
        "asset_condition",
    ):
        try:
            op.drop_column("waypoints", col)
        except Exception:
            pass
