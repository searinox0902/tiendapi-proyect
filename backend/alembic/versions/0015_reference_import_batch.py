"""product_references.import_batch_id — deshacer importaciones (D-73)

Etiqueta de lote, no una FK a una tabla de lotes: la importación granular
(D-73) suma referencias en vez de reemplazar, y sin una forma de deshacer en
bloque un archivo mal armado es indistinguible del catálogo real una vez
adentro. Un UUID nuevo por corrida agrupa lo que creó esa corrida; `NULL` es
alta manual o un lote ya revertido.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-17

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "product_references",
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    #  Indexado: revertir un lote y el badge "importado en bloque" de la UI
    #  filtran por esta columna en cada carga de la pantalla de Referencias.
    op.create_index(
        "ix_product_references_import_batch_id", "product_references", ["import_batch_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_product_references_import_batch_id", table_name="product_references")
    op.drop_column("product_references", "import_batch_id")
