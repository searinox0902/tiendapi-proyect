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
  /** Costo de adquisición (lado compra), independiente de base_price/sale_price (lado venta). `null` si aún no se capturó. */
  precio_proveedor: string | null;
  created_at: string;
  updated_at: string;
  version: number;
}

/** Query params que acepta `GET /references/`. */
export interface IReferenceFilters {
  sku?: string;
  title?: string;
  category_id?: string;
  skip?: number;
  limit?: number;
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
