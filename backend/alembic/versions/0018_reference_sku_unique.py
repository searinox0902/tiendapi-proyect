"""product_references: SKU único por tenant — habilita el modelo de variantes (D-90)

Revoca la **unicidad blanda** que D-73 había fijado a propósito (docs/03 §1.2):
hasta acá `ix_product_references_sku` era un índice común y dos Referencias
podían compartir código. El argumento de entonces sigue siendo válido —que un
lote de mil productos no se caiga por un duplicado— pero ahora tiene una
respuesta mejor que tolerarlos: la fila que choca **se convierte en variante**
(D-90), con código propio y ficha completa, en vez de entrar como copia.

**No era una tolerancia inocua.** Con dos Referencias del mismo SKU,
`GET /references/lookup` —el endpoint que usa la caja para autocompletar por
código— responde **HTTP 500**: `scalar_one_or_none()` lanza
`MultipleResultsFound`. Verificado creando dos filas con el mismo SKU antes de
esta migración. Y se tapaba a sí mismo: el chequeo de duplicados del formulario
consulta ese mismo endpoint y ante el error hace `catch → disponible`, así que
invitaba a crear una tercera.

El índice va sobre `(tenant_id, sku)` y no sobre `sku` solo: el catálogo es
multi-tenant (D-23/D-24) y dos negocios distintos pueden usar el mismo código
del mismo proveedor sin que eso sea un conflicto.

Reemplaza al índice común en vez de sumarse: uno único sirve igual para las
búsquedas por SKU que ya existían, y mantener los dos sería pagar dos veces la
escritura por la misma columna.

**Verificado antes de escribir esta migración:** 0 grupos `(tenant_id, sku)`
duplicados en la base de desarrollo, así que sube sin limpieza previa. Si una
instalación tuviera duplicados, el `CREATE UNIQUE INDEX` falla y hay que
resolverlos a mano —convertirlos en variantes— antes de migrar; se prefiere ese
fallo ruidoso a un script que elija por su cuenta cuál fila renombrar.

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-17

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_product_references_sku", table_name="product_references")
    op.create_index(
        "ix_product_references_tenant_sku",
        "product_references",
        ["tenant_id", "sku"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_product_references_tenant_sku", table_name="product_references")
    op.create_index("ix_product_references_sku", "product_references", ["sku"])
