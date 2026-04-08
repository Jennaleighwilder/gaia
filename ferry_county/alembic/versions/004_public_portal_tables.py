"""public portal — evacuation_zones, road_closures, public_incidents

Revision ID: 004_public_portal
Revises: 003_sentinel
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from geoalchemy2.types import Geometry
from sqlalchemy import inspect

revision = "004_public_portal"
down_revision = "003_sentinel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    tables = insp.get_table_names()
    if "evacuation_zones" not in tables:
        op.create_table(
            "evacuation_zones",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("zone_name", sa.String(100), nullable=False),
            sa.Column("level", sa.Integer(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("geometry", Geometry(geometry_type="POLYGON", srid=4326), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("activated_by", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    if "road_closures" not in tables:
        op.create_table(
            "road_closures",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("road_id", sa.Integer(), nullable=False),
            sa.Column("closure_reason", sa.String(200), nullable=True),
            sa.Column("closure_type", sa.String(30), nullable=True),
            sa.Column("detour_route", Geometry(geometry_type="LINESTRING", srid=4326), nullable=True),
            sa.Column("detour_notes", sa.Text(), nullable=True),
            sa.Column("closed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("closed_by", sa.String(100), nullable=True),
            sa.Column("estimated_reopen", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'closed'")),
            sa.ForeignKeyConstraint(["road_id"], ["roads.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if "public_incidents" not in tables:
        op.create_table(
            "public_incidents",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("incident_type", sa.String(30), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("location", Geometry(geometry_type="POINT", srid=4326), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False, server_default=sa.text("'moderate'")),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("reported_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("reported_by", sa.String(100), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    tables = insp.get_table_names()
    for t in ("public_incidents", "road_closures", "evacuation_zones"):
        if t in tables:
            op.drop_table(t)
