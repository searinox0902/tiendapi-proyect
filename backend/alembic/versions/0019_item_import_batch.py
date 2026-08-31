"""items.import_batch_id — deshacer importaciones de Productos (A-30)

Misma etiqueta de lote que ya tienen `product_references` (0015, D-73) y las
cinco entidades del Directorio (0016, D-75). `Item` era la única entidad
importable que no la tenía, y sin ella un archivo de existencias mal armado
queda indistinguible del inventario real en cuanto entra: no hay forma de
decir "estas 400 unidades las creó ese archivo".

`NULL` = alta manual desde la pantalla de Productos, o un lote ya revertido.

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-18

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    #  Indexado por lo mismo que en Referencias: deshacer un lote filtra por
    #  esta columna, y un import de Productos crea una fila por unidad (D-41),
    #  así que el lote a revertir puede ser de miles de filas.
    op.create_index("ix_items_import_batch_id", "items", ["import_batch_id"])


def downgrade() -> None:
    op.drop_index("ix_items_import_batch_id", table_name="items")
    op.drop_column("items", "import_batch_id")
