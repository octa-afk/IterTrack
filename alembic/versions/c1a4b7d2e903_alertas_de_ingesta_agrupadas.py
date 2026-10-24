"""alertas de ingesta agrupadas

Revision ID: c1a4b7d2e903
Revises: e29ba200b4ed
Create Date: 2026-10-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1a4b7d2e903"
down_revision: Union[str, Sequence[str], None] = "e29ba200b4ed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("problem_type", sa.String(length=120), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default=sa.text("'open'")
        ),
        sa.Column("previous_alert_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_occurrence_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('open','closed')", name="ck_alerts_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["previous_alert_id"], ["alerts.id"]),
    )
    op.create_index("ix_alerts_organization_id", "alerts", ["organization_id"])
    op.create_index("ix_alerts_device_id", "alerts", ["device_id"])
    op.create_index(
        "ix_alerts_open_lookup", "alerts", ["device_id", "problem_type", "status"]
    )
    op.create_table(
        "alert_occurrences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("rejected_point_id", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
        sa.ForeignKeyConstraint(["rejected_point_id"], ["rejected_ingest_points.id"]),
    )
    op.create_index("ix_alert_occurrences_alert_id", "alert_occurrences", ["alert_id"])


def downgrade() -> None:
    op.drop_index("ix_alert_occurrences_alert_id", table_name="alert_occurrences")
    op.drop_table("alert_occurrences")
    op.drop_index("ix_alerts_open_lookup", table_name="alerts")
    op.drop_index("ix_alerts_device_id", table_name="alerts")
    op.drop_index("ix_alerts_organization_id", table_name="alerts")
    op.drop_table("alerts")
