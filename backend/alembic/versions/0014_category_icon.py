"""category icon

`Category.icon` — nombre de ícono lucide (docs/07-decisiones-y-puntos-abiertos.md,
D-72). Nullable, sin CHECK: el set de íconos válidos vive en el frontend, no
en el esquema, así que agregar un ícono nuevo no exige migración.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-16

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("icon", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("categories", "icon")
