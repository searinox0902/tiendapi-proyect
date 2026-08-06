"""reference.precio_proveedor

Costo de adquisición (lado compra) — eje independiente de base_price/sale_price
(lado venta, D-45); no hay fórmula que lo derive (D-47). Nullable: el catálogo
existente no lo tiene todavía y se captura 100% manual desde el CRUD (D-52).

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-05

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "product_references",
        sa.Column("precio_proveedor", sa.Numeric(12, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("product_references", "precio_proveedor")
