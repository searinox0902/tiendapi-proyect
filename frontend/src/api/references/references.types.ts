/** Sobre de listado paginado del backend (`Page[T]` en app/schemas/common.py). */
export interface IPage<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

/** Tal cual lo devuelve `GET /references/` (`ReferenceRead`). */
export interface IReference {
  id: string;
  tenant_id: string;
  provider_id: string;
  category_id: string | null;
  sku: string;
  title: string;
  /** Marca del fabricante del repuesto (NGK, Brembo). Distinta del proveedor. */
  brand: string | null;
  description: string | null;
  image_url: string | null;
  base_price: string;
  iva_percentage: string;
  /** Costo de adquisición (lado compra), independiente de base_price/sale_price (lado venta). `null` si aún no se capturó. Su override por unidad es `IItemStockUnit.provider_price`. */
  provider_price: string | null;
  created_at: string;
  updated_at: string;
  version: number;
}

/** Body que espera `POST /references/` (`ReferenceCreate`). */
export interface IReferenceCreate {
  provider_id: string;
  category_id?: string | null;
  sku: string;
  title: string;
  brand?: string | null;
  description?: string | null;
  image_url?: string | null;
  base_price: number;
  iva_percentage: number;
  provider_price?: number | null;
}

/** Query params que acepta `GET /references/`. */
export interface IReferenceFilters {
  sku?: string;
  title?: string;
  /**
   * SKU **o** nombre en un solo término (OR en el backend) — el campo único de
   * búsqueda de la caja registradora. `sku` y `title` se cruzan con AND, así
   * que no sirven para eso.
   */
  search?: string;
  category_id?: string;
  skip?: number;
  limit?: number;
}

/**
 * Formatos de `GET /references/export` (D-73). El **JSON es el de intercambio**
 * (round-trip fiel, FKs por nombre, plata como string); Excel y Markdown son
 * salida humana — que algo salga en un formato no implica que pueda volver a
 * entrar por ahí.
 */
export type TExportFormat = "json" | "xlsx" | "markdown";

/**
 * Respuesta de `GET /references/variants` (D-90).
 *
 * Una variante es una Referencia propia con SKU único (`ABC#2`); lo único que
 * comparte con sus hermanas es la base del código. Esto es lo que el
 * formulario necesita para ofrecer "ya existe, ¿crear una variante?".
 */
export interface IReferenceVariantInfo {
  base_sku: string;
  exists: boolean;
  /** Incluye la pieza base: si hay una sola, cuenta 1. */
  variant_count: number;
  /** Código libre para la variante nueva; si el SKU no existe, es el propio código base. */
  next_sku: string;
}

/** Fila de la card "Últimas referencias creadas". */
export interface IReferenceLatest {
  id: string;
  sku: string;
  title: string;
  base_price: string;
}

/**
 * Agregados de `GET /references/summary`. Se calculan en el backend porque el
 * listado viene paginado: desde el cliente no se puede saber el total de marcas
 * ni cuáles son las últimas creadas sin traerse el catálogo entero.
 */
export interface IReferenceSummary {
  total_references: number;
  total_brands: number;
  /** `null` cuando el catálogo está vacío. */
  last_updated_at: string | null;
  latest: IReferenceLatest[];
}

/** Tal cual lo devuelve `GET /categories/` (`CategoryRead`). */
export interface ICategory {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  version: number;
}

/** Tal cual lo devuelve `GET /providers/` (`ProviderRead`). */
export interface IProvider {
  id: string;
  tenant_id: string;
  provider_code: string | null;
  nit: string | null;
  title: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  version: number;
}

/* ── Importación de catálogo (D-73) ────────────────────────────────────────
 * El payload que se manda es el mismo objeto que devuelve
 * `GET /references/export?format=json` — no hay un tipo de "solicitud" propio,
 * es literalmente el archivo. */

export interface IReferenceImportInvalidRow {
  index: number;
  sku: string | null;
  reason: string;
}

/** Respuesta de `POST /references/import/preview` — no escribe nada. */
export interface IReferenceImportPreview {
  total_rows: number;
  new_count: number;
  existing_skus: string[];
  invalid: IReferenceImportInvalidRow[];
  new_providers: string[];
  new_categories: string[];
  /** `null` para un archivo JSON — solo el .xlsx tiene encabezados que detectar. */
  columns_detected: string[] | null;
  /** Columnas opcionales que el archivo no trae — esas filas quedan con el valor por defecto (Nombre → SKU, Proveedor → placeholder, IVA % → 0). */
  columns_missing: string[] | null;
  /** Encabezados del archivo que no corresponden a ninguna columna conocida y se descartan (ej. `URL` de un scraper). */
  columns_ignored: string[] | null;
}

/** Respuesta de `POST /references/import` — ya escribió en la BBDD. */
export interface IReferenceImportResult {
  created: number;
  skipped: number;
  invalid: number;
  /** `null` si `created === 0`: no hay lote que deshacer. */
  batch_id: string | null;
}
