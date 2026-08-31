"""reference.precio_proveedor → reference.provider_price

Corrige el único identificador en spanglish del módulo de Referencias (D-62).
El mismo concepto —costo de adquisición, lado compra (D-47)— ya se llamaba
`provider_price` en `items` desde la migración `0007`, así que la base tenía
dos nombres para lo mismo, conviviendo incluso dentro de un solo
`COALESCE(Item.provider_price, Reference.precio_proveedor)`.

`ALTER ... RENAME COLUMN` y no columna nueva + copia + drop: el rename es
atómico, conserva los datos y el tipo, y no deja una ventana en la que las dos
columnas existan y puedan divergir.

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-10

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("product_references", "precio_proveedor", new_column_name="provider_price")


def downgrade() -> None:
    op.alter_column("product_references", "provider_price", new_column_name="precio_proveedor")
