"""product_references.image_url pasa a guardar SOLO URLs externas (D-84)

Migración de **datos**, no de esquema: la columna no cambia de tipo ni de
nulabilidad. Lo que cambia es su significado.

Hasta acá el formulario concatenaba `VITE_API_URL` a la ruta devuelta por
`POST /references/images/{sku}` y persistía el resultado, dejando en la BBDD
URLs absolutas con el host quemado (`http://localhost:8000/static/images/...`).
Eso rompía en cuatro frentes: cualquier máquina de la LAN que no fuera la que
subió el archivo resolvía `localhost` contra sí misma (D-32/D-33); el empaquetado
Tauri mueve las imágenes a `appDataDir` y deja esas filas apuntando a la nada
(D-40/D-58); el catálogo exportado se llevaba el `localhost` a otra instalación,
contra el principio de D-73; y, sobre todo, hacía **indistinguible** una imagen
local de una externa, que es lo que impide priorizar la local.

Desde D-84 la presencia de imagen local es un hecho **derivado del disco** —el
archivo se llama como el SKU (D-58)— y la columna guarda únicamente la URL
externa. Por eso estas filas se limpian a `NULL`: **el archivo local sigue en su
lugar** y `app/core/images.py:resolve_image_url()` lo encuentra solo, así que no
se pierde ninguna imagen; se borra un puntero que ya estaba mal.

El filtro apunta a la ruta que servía el backend (`%/static/images/%`) y no a un
host puntual: en desarrollo es `localhost:8000`, pero cualquiera que haya
levantado el backend en otra dirección tiene el suyo guardado igual.

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-17

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE product_references
           SET image_url = NULL
         WHERE image_url LIKE '%/static/images/%'
        """
    )


def downgrade() -> None:
    #  Irreversible a propósito: la URL vieja no se puede reconstruir sin saber
    #  con qué host se generó, y reconstruirla sería restaurar el bug. El dato
    #  útil —el archivo en disco— nunca se tocó.
    pass
