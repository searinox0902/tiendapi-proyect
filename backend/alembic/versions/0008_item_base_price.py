"""item.base_price — última pata del override por unidad

Misma dinámica que crear una Referencia: precio base + IVA determinan el
precio de venta, nunca se captura a mano (D-45/D-46). Con `iva_percentage` y
`provider_price` ya en el Ítem (migración 0007), faltaba `base_price` para que
"editar una existencia" sea exactamente ese mismo cálculo, con vida propia por
unidad — nullable, mismo patrón `COALESCE` hacia el catálogo.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-08

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("items", sa.Column("base_price", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("items", "base_price")
