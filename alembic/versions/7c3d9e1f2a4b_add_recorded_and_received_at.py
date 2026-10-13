"""add recorded_at and received_at to tracking points

Revision ID: 7c3d9e1f2a4b
Revises: a1b2c3d4e5f6
Create Date: 2026-10-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c3d9e1f2a4b"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tracking_points",
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tracking_points",
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Filas previas: la única marca de tiempo que existe es `timestamp`, que se usa
    # como medición y como recepción (no hay dato histórico que los separe).
    op.execute("UPDATE tracking_points SET recorded_at = timestamp, received_at = timestamp")
    op.alter_column("tracking_points", "recorded_at", nullable=False)
    op.alter_column("tracking_points", "received_at", nullable=False)


def downgrade() -> None:
    op.drop_column("tracking_points", "received_at")
    op.drop_column("tracking_points", "recorded_at")
