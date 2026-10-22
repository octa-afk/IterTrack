"""fix organizations sequence and remove default seed

Revision ID: f9bb7aa245c0
Revises: f1a2b3c4d5e6
Create Date: 2026-10-22 14:44:50.345695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9bb7aa245c0'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # f08375e32888 inserta la org "Default" con id=1 explícito sin avanzar la
    # secuencia SERIAL, por lo que el primer INSERT real reutilizaría id=1 y
    # fallaría con UniqueViolation. Sincroniza la secuencia con MAX(id).
    op.execute(
        "SELECT setval("
        "pg_get_serial_sequence('organizations', 'id'), "
        "(SELECT COALESCE(MAX(id), 1) FROM organizations)"
        ")"
    )
    # Elimina la org de bootstrap legado (código de invitación hardcodeado
    # DEFAULT-CODE) solo cuando nada la referencia, para que las instalaciones
    # nuevas arranquen limpias.
    op.execute(
        "DELETE FROM organizations "
        "WHERE name = 'Default' AND invitation_code = 'DEFAULT-CODE' "
        "AND NOT EXISTS (SELECT 1 FROM users WHERE organization_id = organizations.id) "
        "AND NOT EXISTS (SELECT 1 FROM trucks WHERE organization_id = organizations.id)"
    )


def downgrade() -> None:
    # Restaura el seed legado de forma best-effort (id asignado por la secuencia).
    op.execute(
        "INSERT INTO organizations (name, invitation_code, created_at) "
        "SELECT 'Default', 'DEFAULT-CODE', NOW() "
        "WHERE NOT EXISTS (SELECT 1 FROM organizations WHERE name = 'Default')"
    )
