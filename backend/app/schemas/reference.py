import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator

from app.core.sku import generate_sku, normalize_sku


class ReferenceBase(BaseModel):
    provider_id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    sku: str
    title: str
    brand: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    base_price: Decimal
    iva_percentage: Decimal = Decimal("0")
    # Costo de adquisición (lado compra), independiente de base_price/sale_price
    # (lado venta) — ver D-47. Opcional: el catálogo existente no lo tiene todavía.
    # Mismo nombre que `Item.provider_price`, que es su override por unidad (D-62).
    provider_price: Optional[Decimal] = None


class ReferenceWrite(ReferenceBase):
    """
    Base de los payloads de **escritura** — normaliza el SKU (D-85) y lo genera
    si viene vacío (D-86).

    Deliberadamente NO está en `ReferenceBase`: `ReferenceRead` hereda de ahí, y
    normalizar al leer haría que la API reportara un SKU distinto del guardado
    para cualquier fila vieja con separadores raros — devolvería un valor con el
    que después no se puede volver a buscar la Referencia.
    """

    #  Se redeclara con default para que el payload pueda omitirlo: en
    #  `ReferenceBase` es obligatorio y un POST sin `sku` moriría con 422 antes
    #  de que el validador llegue a generarlo. `ReferenceRead` sigue heredando
    #  la versión obligatoria — al leer, el SKU siempre existe.
    sku: str = ""

    @model_validator(mode="after")
    def _normalize_or_generate_sku(self) -> "ReferenceWrite":
        #  A nivel de modelo y no de campo porque generar necesita `title`/
        #  `brand`, y un `field_validator` sobre `sku` no ve los otros campos.
        normalized = normalize_sku(self.sku or "")
        self.sku = normalized or generate_sku(self.title, self.brand)
        return self


class ReferenceCreate(ReferenceWrite):
    pass


class ReferenceUpdate(ReferenceWrite):
    pass


class ReferenceRead(ReferenceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    version: int


class ReferenceLatest(BaseModel):
    """Fila mínima de "últimas referencias creadas" — solo lo que pinta la card."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    title: str
    base_price: Decimal


class ReferenceVariantInfo(BaseModel):
    """
    Respuesta de `GET /references/variants` — estado del grupo de un SKU (D-90).

    Alimenta la oferta "este código ya existe, ¿crear una variante?" del
    formulario de alta. `next_sku` es el código libre que le tocaría a la
    variante nueva; si el SKU todavía no existe, devuelve el propio código base
    (no hay variante que crear, es un alta normal).
    """

    base_sku: str
    exists: bool
    #  Incluye la pieza base: de cara al usuario el grupo son "3 variantes",
    #  no "la pieza más 2".
    variant_count: int
    next_sku: str


class ReferenceImportInvalidRow(BaseModel):
    """Fila que no se pudo leer del archivo — no bloquea las demás (D-73)."""

    index: int
    sku: Optional[str] = None
    reason: str


class ReferenceImportPreview(BaseModel):
    """
    Respuesta de `POST /references/import/preview` — no escribe nada, solo
    cuenta. `existing_skus`/`new_providers`/`new_categories` son lo que el
    usuario necesita ver *antes* de confirmar: cuántos SKU van a quedar
    duplicados si no los salta, y qué Proveedores/Categorías va a crear el
    import porque el archivo trae nombres que el negocio no tenía.
    """

    total_rows: int
    new_count: int
    existing_skus: list[str]
    invalid: list[ReferenceImportInvalidRow]
    new_providers: list[str]
    new_categories: list[str]
    #  `None` para un archivo JSON — no tiene encabezados que detectar, solo
    #  aplica al .xlsx (D-74).
    columns_detected: Optional[list[str]] = None
    columns_missing: Optional[list[str]] = None
    #  Encabezados del archivo que no corresponden a ninguna columna conocida y
    #  se descartan (ej. `URL` de un scraper). Se reportan en vez de ignorarse
    #  callado: sin esto, una columna mal escrita se ve igual que una ausente.
    columns_ignored: Optional[list[str]] = None


class ReferenceImportResult(BaseModel):
    """Respuesta de `POST /references/import` — ya escribió en la BBDD."""

    created: int
    skipped: int
    invalid: int
    #  `None` cuando `created == 0`: no tiene sentido un lote vacío para deshacer.
    batch_id: Optional[uuid.UUID] = None


class ReferenceImportUndoResult(BaseModel):
    deleted: int


class ReferenceSummary(BaseModel):
    """
    Agregados del catálogo para las cards de resumen.

    Se calculan en SQL y no en el cliente: el listado viene paginado y ordenado
    por SKU, así que desde el frontend no hay forma de saber el total de marcas
    ni cuáles son las últimas creadas sin traerse el catálogo entero.
    """

    total_references: int
    total_brands: int
    #  `None` cuando el catálogo está vacío.
    last_updated_at: Optional[datetime] = None
    latest: list[ReferenceLatest]
