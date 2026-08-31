/**
 * Ancho de cada bucket del eje de tiempo.
 *
 * **Lo decide el servidor**, derivado del largo del rango (D-69) — el cliente
 * no lo pide. Llega en la respuesta porque los gráficos necesitan saber si
 * rotulan horas, días o semanas.
 */
export type TBucketGranularity = "hour" | "day" | "week";

/** Rango de fechas del tablero, en `YYYY-MM-DD`. Ambos extremos inclusivos. */
export interface IDashboardRange {
  from: string;
  to: string;
}

/** Un punto del gráfico de ventas. `bucket` viene en hora **local** del negocio, sin zona. */
export interface ISalesPoint {
  bucket: string;
  /** Monto como string para no perder precisión — pasa por `Decimal` al mostrarse. */
  total: string;
}

/**
 * Un punto de "entra vs. sale". `added` es un conteo de unidades físicas;
 * `sold` llega como decimal string (`BillItem.quantity` es Numeric(12,3)).
 */
export interface IFlowPoint {
  bucket: string;
  sold: string;
  added: number;
}

/** Fila de "Top productos vendidos" — agregada por Referencia, no por unidad física. */
export interface ITopProduct {
  reference_id: string;
  sku: string;
  title: string;
  image_url: string | null;
  units: string;
  revenue: string;
}

/**
 * Fila de "Reponer ya" (D-66). La UI muestra el **par crudo**
 * (`available_units` / `units_sold`); `days_of_cover` solo define el tono de
 * alarma y el orden — nunca se pinta como número, por decisión de producto.
 */
export interface IRestockRow {
  reference_id: string;
  sku: string;
  title: string;
  image_url: string | null;
  available_units: number;
  units_sold: string;
  /** `null` = agotado (no hay nada que cubrir). Distinto de `0`, que sería "se acaba hoy". */
  days_of_cover: number | null;
}

/**
 * Todo el Dashboard en una respuesta (`GET /dashboard/summary`).
 *
 * `sales_series` y `flow_series` comparten la misma grilla de buckets, para
 * que un pico en un gráfico se pueda leer contra el mismo día en el otro.
 */
export interface IDashboardSummary {
  /**
   * Rango **efectivamente medido**, que puede no ser el pedido: el servidor
   * recorta el extremo derecho a "ahora" y limita el largo total (D-69).
   */
  period_from: string;
  period_to: string;
  granularity: TBucketGranularity;
  total_billed: string;
  sales_series: ISalesPoint[];
  /** Misma grilla de buckets que `sales_series`, para poder leer un pico contra el otro. */
  flow_series: IFlowPoint[];
  units_sold: string;
  distinct_references_sold: number;
  out_of_stock_with_demand: number;
  stale_references: number;
  top_products: ITopProduct[];
  restock: IRestockRow[];
}
