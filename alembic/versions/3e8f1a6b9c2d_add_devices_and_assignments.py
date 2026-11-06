"""add devices and device assignments

Revision ID: 3e8f1a6b9c2d
Revises: 7c3d9e1f2a4b
Create Date: 2026-10-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3e8f1a6b9c2d"
down_revision: Union[str, Sequence[str], None] = "7c3d9e1f2a4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("identifier", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_table(
        "device_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("truck_id", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["truck_id"], ["trucks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_device_assignments_open_device",
        "device_assignments",
        ["device_id"],
        unique=True,
        postgresql_where=sa.text("valid_to IS NULL"),
        sqlite_where=sa.text("valid_to IS NULL"),
    )
    op.create_index(
        "uq_device_assignments_open_truck",
        "device_assignments",
        ["truck_id"],
        unique=True,
        postgresql_where=sa.text("valid_to IS NULL"),
        sqlite_where=sa.text("valid_to IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_device_assignments_open_truck", table_name="device_assignments")
    op.drop_index("uq_device_assignments_open_device", table_name="device_assignments")
    op.drop_table("device_assignments")
    op.drop_table("devices")
