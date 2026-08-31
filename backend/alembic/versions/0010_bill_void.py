"""bill.voided_at / bill.void_reason — anulación de factura

Anulación como **marca**, no como borrado (D-60): la factura anulada conserva
su consecutivo y sus líneas. Un documento numerado que se borra deja un hueco
en la serie que después nadie puede explicar, y el consecutivo es un dato
fiscal (ver `_next_bill_number`, que se calcula del máximo existente).

Dos columnas y no un booleano: la fecha dice *cuándo* se anuló —dato que hace
falta para cuadrar un periodo— y el motivo distingue un error de digitación de
una devolución, que para el inventario y para la DIAN no son lo mismo. El
motivo es obligatorio en el endpoint, no en la base: las facturas anteriores a
esta migración no tienen ninguno y un `NOT NULL` no podría aplicarse hacia
atrás.

Zona de alto riesgo (control fiscal + inventario, CLAUDE.md).

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-10

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bills", sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bills", sa.Column("void_reason", sa.String(), nullable=True))
    #  Indexado porque el resumen de Facturación lo consulta en cada carga para
    #  excluir las anuladas de las sumas de dinero.
    op.create_index("ix_bills_voided_at", "bills", ["voided_at"])


def downgrade() -> None:
    op.drop_index("ix_bills_voided_at", table_name="bills")
    op.drop_column("bills", "void_reason")
    op.drop_column("bills", "voided_at")
