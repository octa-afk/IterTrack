"""add role scopes and device organization ownership

Replaces the ambiguous 'admin'/'cliente' roles with explicit scopes and gives
devices an owning organization so administrative reads can be filtered without
walking the assignment table.

Revision ID: b7c1d2e3f4a5
Revises: 5426d9d8a15a
Create Date: 2026-10-23
"""

import sqlalchemy as sa

from alembic import op

revision = "b7c1d2e3f4a5"
down_revision = "5426d9d8a15a"
branch_labels = None
depends_on = None

_DEVICE_FK = "fk_devices_organization_id_organizations"
_ROLE_CHECK = "ck_users_role"


def upgrade() -> None:
    op.add_column("devices", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.create_foreign_key(_DEVICE_FK, "devices", "organizations", ["organization_id"], ["id"])

    # Devices take the organization of the truck they are currently assigned to.
    op.execute(
        """
        UPDATE devices AS d
        SET organization_id = t.organization_id
        FROM device_assignments AS da
        JOIN trucks AS t ON t.id = da.truck_id
        WHERE da.device_id = d.id
          AND d.organization_id IS NULL
          AND da.valid_to IS NULL
        """
    )
    # Revoked devices keep the organization of their most recent assignment.
    op.execute(
        """
        UPDATE devices AS d
        SET organization_id = latest.organization_id
        FROM (
            SELECT DISTINCT ON (da.device_id) da.device_id, t.organization_id
            FROM device_assignments AS da
            JOIN trucks AS t ON t.id = da.truck_id
            ORDER BY da.device_id, da.valid_from DESC
        ) AS latest
        WHERE latest.device_id = d.id
          AND d.organization_id IS NULL
        """
    )

    op.execute("UPDATE users SET role = 'org_admin' WHERE role = 'admin'")
    op.execute("UPDATE users SET role = 'member' WHERE role = 'cliente'")
    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=20),
        existing_nullable=False,
        server_default="member",
    )
    op.create_check_constraint(
        _ROLE_CHECK, "users", "role IN ('platform_admin', 'org_admin', 'member')"
    )


def downgrade() -> None:
    op.drop_constraint(_ROLE_CHECK, "users", type_="check")
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'org_admin'")
    op.execute("UPDATE users SET role = 'cliente' WHERE role = 'member'")
    op.execute("UPDATE users SET role = 'cliente' WHERE role = 'platform_admin'")
    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=20),
        existing_nullable=False,
        server_default="cliente",
    )
    op.drop_constraint(_DEVICE_FK, "devices", type_="foreignkey")
    op.drop_column("devices", "organization_id")
