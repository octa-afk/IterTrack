"""add device ingestion idempotency and rejection evidence

Revision ID: e7f1a2b3c4d5
Revises: d4a7c9e2b6f1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e7f1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "d4a7c9e2b6f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingested_points",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("truck_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False), sa.Column("long", sa.Float(), nullable=False),
        sa.Column("speed", sa.Float(), nullable=False), sa.Column("heading", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["assignment_id"], ["device_assignments.id"]),
        sa.ForeignKeyConstraint(["truck_id"], ["trucks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assignment_id", "batch_id", "sequence", name="uq_ingested_assignment_batch_sequence"),
    )
    op.create_table(
        "rejected_ingest_points",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False), sa.Column("assignment_id", sa.Integer(), nullable=True),
        sa.Column("batch_id", sa.String(length=36), nullable=False), sa.Column("sequence", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=120), nullable=False), sa.Column("raw_payload", sa.Text(), nullable=False),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]), sa.ForeignKeyConstraint(["assignment_id"], ["device_assignments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "batch_id", "sequence", name="uq_rejected_device_batch_sequence"),
    )


def downgrade() -> None:
    op.drop_table("rejected_ingest_points")
    op.drop_table("ingested_points")
