"""item.status

Ciclo de vida de la unidad física — docs/03-modelo-datos.md §1.3 (D-41):
`disponible | vendido | reservado | de_baja`. Toda existencia nueva nace
`disponible`; `de_baja` es una baja manual (dañada, extraviada, ...), reversible
con "activar" (vuelve a `disponible`). `vendido`/`reservado` quedan reservados
para cuando exista el flujo de facturación — nada los asigna todavía.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-08

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column("status", sa.String(), nullable=False, server_default="disponible"),
    )
    op.create_check_constraint(
        "ck_items_status",
        "items",
        "status IN ('disponible', 'vendido', 'reservado', 'de_baja')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_items_status", "items", type_="check")
    op.drop_column("items", "status")
