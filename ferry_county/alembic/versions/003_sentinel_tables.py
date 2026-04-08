"""sentinel_scans and sentinel_road_risks

Revision ID: 003_sentinel
Revises: 002_result
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "003_sentinel"
down_revision = "002_result"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    tables = insp.get_table_names()
    if "sentinel_scans" not in tables:
        op.create_table(
            "sentinel_scans",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("scan_time", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("atmosphere_fwi", sa.Numeric(5, 2), nullable=True),
            sa.Column("atmosphere_rh", sa.Numeric(5, 2), nullable=True),
            sa.Column("atmosphere_wind", sa.Numeric(6, 2), nullable=True),
            sa.Column("red_flag_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("palmer_drought", sa.Numeric(5, 2), nullable=True),
            sa.Column("soil_moisture", sa.Numeric(5, 2), nullable=True),
            sa.Column("scan_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("road_count", sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if "sentinel_road_risks" not in tables:
        op.create_table(
            "sentinel_road_risks",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("scan_id", sa.Integer(), nullable=False),
            sa.Column("road_id", sa.Integer(), nullable=False),
            sa.Column("risk_score", sa.Numeric(5, 2), nullable=True),
            sa.Column("convergence_count", sa.Integer(), nullable=True),
            sa.Column("risk_level", sa.String(20), nullable=True),
            sa.Column("atmosphere_contributing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("canopy_contributing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("ground_contributing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("primary_driver", sa.String(20), nullable=True),
            sa.Column("recommendation", sa.Text(), nullable=True),
            sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["road_id"], ["roads.id"]),
            sa.ForeignKeyConstraint(["scan_id"], ["sentinel_scans.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_sentinel_road_risk_scan", "sentinel_road_risks", ["scan_id"])
        op.create_index("idx_sentinel_road_risk_level", "sentinel_road_risks", ["risk_level"])
        op.create_index("idx_sentinel_road_risk_road", "sentinel_road_risks", ["road_id"])


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    tables = insp.get_table_names()
    if "sentinel_road_risks" in tables:
        op.drop_table("sentinel_road_risks")
    if "sentinel_scans" in tables:
        op.drop_table("sentinel_scans")
