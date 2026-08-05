"""reference.brand

Marca del repuesto (quién lo fabrica), distinta del proveedor (a quién se le
compra). Nullable: el catálogo existente no la tiene y hay repuestos genéricos
sin marca reconocible.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-04

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product_references", sa.Column("brand", sa.String(), nullable=True))
    op.create_index("ix_product_references_brand", "product_references", ["brand"])


def downgrade() -> None:
    op.drop_index("ix_product_references_brand", table_name="product_references")
    op.drop_column("product_references", "brand")
