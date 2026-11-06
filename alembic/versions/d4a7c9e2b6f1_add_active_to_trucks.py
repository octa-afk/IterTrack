"""add active state to trucks

Revision ID: d4a7c9e2b6f1
Revises: 3e8f1a6b9c2d
Create Date: 2026-10-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4a7c9e2b6f1"
down_revision: Union[str, Sequence[str], None] = "3e8f1a6b9c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trucks",
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("trucks", "active")
