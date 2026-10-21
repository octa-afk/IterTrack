"""add telemetry query indexes

Revision ID: f1a2b3c4d5e6
Revises: e7f1a2b3c4d5
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e7f1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_tracking_points_truck_recorded_at_id",
        "tracking_points",
        ["truck_id", sa.text("recorded_at DESC"), sa.text("id DESC")],
        postgresql_using="btree",
    )
    op.create_index(
        "ix_ingested_points_truck_recorded_at_id",
        "ingested_points",
        ["truck_id", sa.text("recorded_at DESC"), sa.text("id DESC")],
        postgresql_using="btree",
    )


def downgrade() -> None:
    op.drop_index("ix_ingested_points_truck_recorded_at_id", table_name="ingested_points")
    op.drop_index("ix_tracking_points_truck_recorded_at_id", table_name="tracking_points")
