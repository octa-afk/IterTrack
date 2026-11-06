"""add telemetry to tracking points

Revision ID: a1b2c3d4e5f6
Revises: f08375e32888
Create Date: 2026-10-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f08375e32888"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tracking_points",
        sa.Column("speed", sa.Float(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "tracking_points",
        sa.Column("heading", sa.Float(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("tracking_points", "heading")
    op.drop_column("tracking_points", "speed")
