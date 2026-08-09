/**
 * `IPage` se reusa desde Referencias: es el sobre genérico del backend
 * (`Page[T]` en app/schemas/common.py), no algo propio de esa pantalla.
 */
export type { IPage } from "@/api/references/references.types";

/**
 * Fila de `GET /items/stock` (`ItemStockRead`) — una card de la grilla de
 * Productos. **No es un `Item`**: cada `Item` es una unidad física individual
 * (D-41), así que la fila es la Referencia con sus Ítems ya contados. Por eso
 * la PK que viaja es `reference_id` y no un `item_id`.
 */
export interface IItemStock {
  reference_id: string;
  sku: string;
  title: string;
  /** Marca del fabricante (NGK, Brembo). Distinta del proveedor — D-57. */
  brand: string | null;
  image_url: string | null;
  category_id: string | null;
  /** Unidades en existencia = cuántos `Item` apuntan a esta Referencia. */
  units: number;
  /** Precio de venta con IVA (D-45/D-46). Llega como string para no perder precisión. */
  sale_price: string;
}

/**
 * Cifras de cabecera de la pantalla Productos (`ItemStockSummaryRead`).
 *
 * **Respetan los filtros activos**: resumen de lo que se está mirando, no del
 * inventario entero. El servidor las calcula sobre todas las filas que pasan el
 * filtro, no sobre la tanda que el scroll infinito alcanzó a cargar.
 */
export interface IItemStockSummary {
  /** Productos (Referencias) que pasan el filtro — el número de cards. */
  total_references: number;
  /** Unidades físicas de esos productos. No es lo mismo: 29 productos pueden ser 453 unidades (D-41). */
  total_units: number;
  /** Productos con 0 unidades: venta perdida, la cifra que exige acción. */
  out_of_stock_references: number;
  /** Productos con existencias pero bajo el umbral: reponer ANTES de agotarse. Excluye agotados. */
  low_stock_references: number;
  /** Umbral usado para `low_stock_references` — viene del servidor para no hardcodearlo en la UI. */
  low_stock_threshold: number;
  /** Capital inmovilizado: Σ(precio_proveedor × unidades). */
  total_cost: string;
  /** Σ(precio_venta × unidades) — lo que entraría si se vendiera todo. */
  total_sale_value: string;
  potential_margin: string;
  /** Margen bruto sobre la venta, en %. */
  margin_percentage: string;
  /** Unidades sin `precio_proveedor` cargado: `total_cost` está incompleto si es > 0. */
  units_without_cost: number;
}

/**
 * Una unidad física concreta (`ItemExistenceRead`) — fila de la pantalla de
 * aterrizaje del Producto. A diferencia de `IItemStock`, que agrega y cuenta,
 * acá cada objeto ES un `Item` con su identidad propia (D-41): `item_id` es lo
 * que el cajero teclea para vender esta unidad y no otra (A-22).
 */
/** Ciclo de vida de la unidad física — docs/03-modelo-datos.md §1.3 (D-41). */
export type TItemStatus = "disponible" | "vendido" | "reservado" | "de_baja";

export interface IItemExistence {
  item_id: string;
  status: TItemStatus;
  /** Opcional (migración 0005): el alta manual rápida no exige elegirlo en el momento. */
  provider_id: string | null;
  provider_name: string | null;
  location_id: string | null;
  location_name: string | null;
  /** Porcentaje, no monto (D-19). El monto se deriva al pintar. */
  iva_percentage: string;
  /** Costo de adquisición. Hoy vive en la Referencia (D-47): igual para todas sus unidades. */
  provider_price: string | null;
  base_price: string;
  sale_price: string;
}

/** Totales del producto, calculados en el servidor — nunca sumados en el cliente. */
export interface IItemDetailTotals {
  total_units: number;
  total_base: string;
  total_iva: string;
  total_value: string;
}

/** Cabecera: datos de catálogo de la Referencia que agrupa las existencias. */
export interface IProductSummary {
  reference_id: string;
  sku: string;
  title: string;
  brand: string | null;
  image_url: string | null;
  category_id: string | null;
  category_name: string | null;
  /** Proveedores distintos entre las existencias — se deriva de los Ítems. */
  active_providers_count: number;
  /** Precio con IVA del catálogo (D-45/D-46) — para prellenar el precio al agregar una existencia. */
  sale_price: string;
}

/** Payload de `POST /items/` — una unidad física (D-41), no un lote. */
export interface IItemCreatePayload {
  reference_id: string;
  /** Opcionales: el alta manual rápida no exige elegir proveedor/ubicación en el momento. */
  provider_id?: string | null;
  location_id?: string | null;
  quantity: string;
  current_price: string;
}

/** Respuesta de `POST /items/` — el Ítem recién creado. */
export interface IItemRead {
  id: string;
  tenant_id: string;
  reference_id: string;
  provider_id: string | null;
  location_id: string | null;
  quantity: string;
  current_price: string;
  status: TItemStatus;
}

/**
 * `PATCH /items/{id}` — actualización parcial. Un campo **ausente** no se
 * toca; uno presente en `null` sí se limpia (`exclude_unset` en el backend).
 * Por eso todo es opcional acá: el payload real que viaja solo trae las
 * claves que de verdad cambiaron.
 */
export interface IItemUpdatePayload {
  provider_id?: string | null;
  location_id?: string | null;
  status?: TItemStatus;
  /**
   * Precio de venta de ESTA unidad (D-45). No se manda desde el modal de
   * edición — misma dinámica que crear una Referencia: se deriva de
   * `base_price` + `iva_percentage`, el servidor lo recalcula solo cuando
   * alguno de esos dos cambia sin que este campo venga explícito. Sigue
   * existiendo por si algún flujo futuro necesita fijarlo directo. No admite
   * `null` — el backend lo rechaza (422): toda unidad tiene su propio precio.
   */
  current_price?: string;
  /** `null` restablece al precio base vigente de catálogo. */
  base_price?: string | null;
  /** `null` restablece al IVA vigente de catálogo (el backend hace `COALESCE`). */
  iva_percentage?: string | null;
  /** `null` restablece al costo vigente de catálogo. */
  provider_price?: string | null;
}

/** Respuesta completa de `GET /items/by-reference/{reference_id}`. */
export interface IItemDetail {
  summary: IProductSummary;
  totals: IItemDetailTotals;
  existences: IItemExistence[];
}

/**
 * Estado de existencia por el que filtra la grilla. Es lo que hace clicables
 * las cards de resumen: cada una selecciona uno de estos estados.
 */
export type TStockStatus = "all" | "out_of_stock" | "low_stock" | "in_stock";

/** Orden por última entrada de mercancía (o alta en catálogo si nunca tuvo). */
export type TStockSort = "newest" | "oldest";

/** Query params que acepta `GET /items/stock`. */
export interface IItemStockFilters {
  sku?: string;
  title?: string;
  brand?: string;
  category_id?: string;
  stock_status?: TStockStatus;
  sort?: TStockSort;
  skip?: number;
  limit?: number;
}
