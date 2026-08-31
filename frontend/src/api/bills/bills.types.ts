export type { IPage } from "@/api/references/references.types";

/**
 * Estado fiscal DIAN de la factura (D-48).
 *
 * `null` en `IBill.fiscal_status` **no** es uno de estos: significa que la
 * factura nunca entró a un trámite fiscal, distinto de `"pendiente"` (que sí
 * afirma que está en cola). Sin integración DIAN viva (D-09/D-38), `null` es
 * lo esperable.
 */
export type TFiscalStatus =
  | "contingencia"
  | "pendiente"
  | "autorizada"
  | "rechazada";

/** Fila de la tabla de Facturación (`BillListRead`). */
export interface IBill {
  id: string;
  bill_number: string;
  customer_id: string;
  /** Viene resuelto del servidor: la tabla no puede pedir N clientes por página. */
  customer_name: string;
  /** Montos como string para no perder precisión — pasan por `Decimal` al pintarse. */
  subtotal: string;
  total_iva: string;
  total: string;
  fiscal_status: TFiscalStatus | null;
  /**
   * Anulada (D-60). `null` = vigente. Viaja en la fila porque una factura
   * anulada que se ve igual que una vigente hace creer que ese dinero entró.
   */
  voided_at: string | null;
  /** Cuántas líneas tiene la factura: el "tamaño" de la venta de un vistazo. */
  items_count: number;
  created_at: string;
}

/**
 * Un renglón del detalle: **por Referencia**, no por unidad física.
 *
 * El servidor guarda un `BillItem` por cada unidad vendida —cada una es una
 * existencia distinta que hay que descontar—, pero "3 pastillas" es una sola
 * línea del documento. La agrupación la hace el backend, que es quien tiene el
 * JOIN a `Reference`.
 */
export interface IBillDetailLine {
  reference_id: string;
  sku: string;
  title: string;
  image_url: string | null;
  /** Decimal como string, igual que los montos. */
  quantity: string;
  /** Precio cobrado por unidad, con IVA. Parte de la clave de agrupación: dos precios distintos son dos renglones. */
  unit_price: string;
  iva_percentage: string;
  iva_amount: string;
  total: string;
}

export interface IBillCustomer {
  id: string;
  fullname: string;
  nit: string | null;
}

/** Factura completa — pantalla Ver Factura (`GET /bills/{id}/detail`). */
export interface IBillDetail {
  id: string;
  bill_number: string;
  customer: IBillCustomer;
  subtotal: string;
  total_iva: string;
  total: string;
  fiscal_status: TFiscalStatus | null;
  voided_at: string | null;
  void_reason: string | null;
  created_at: string;
  lines: IBillDetailLine[];
  /**
   * Enlace a la **representación gráfica firmada** del proveedor de
   * facturación electrónica (docs/05, §3.6). Hoy siempre `null`: la
   * integración DIAN está diferida (D-09/D-38), así que no existe ningún PDF
   * con validez fiscal. Mientras tanto la pantalla reconstruye el documento
   * desde estos datos (D-61); el día que traiga una URL, el mismo panel pasa a
   * mostrar el archivo en un `<iframe>`.
   */
  pdf_url: string | null;
}

/**
 * Cifras de cabecera de Facturación (`BillSummaryRead`), con las fórmulas
 * fijadas por D-49. **Respetan los filtros activos**: describen lo que se está
 * mirando, no el histórico completo.
 */
export interface IBillSummary {
  /** Σ `Bill.total` (con IVA). */
  total_billed: string;
  /** Σ `Bill.total_iva`. */
  total_iva: string;
  /** Σ (precio de venta − costo) × cantidad. */
  total_profit: string;
  /** Unidades vendidas sin costo cargado: `total_profit` está incompleta si es > 0. */
  units_without_cost: number;
  /** Cuenta **todas** las facturas del filtro, anuladas incluidas: el documento se emitió. */
  total_bills: number;
  /** Cuántas están anuladas (D-60). Sin esto, el conteo y las cifras de dinero parecerían no cuadrar. */
  voided_bills: number;
  /*
   * El desglose fiscal (declaradas/sin declarar/rechazadas/sin estado) salió
   * en D-81: con la DIAN diferida (D-09/D-38) tres eran siempre 0 y el cuarto
   * siempre igual a `total_bills`. Vuelve el día que la integración exista.
   */
}

/**
 * Una línea del carrito tal como la manda la caja: **Referencia y cantidad**,
 * no unidades físicas. El cajero vende "3 pastillas", no las unidades `a1b2`,
 * `c3d4` y `e5f6` — resolver cuáles son es trabajo del servidor (D-41), que
 * además es el único que puede hacerlo sin condiciones de carrera.
 */
export interface ICheckoutLine {
  reference_id: string;
  quantity: number;
  /**
   * Precio cobrado por unidad, con IVA y descuento ya aplicados. El desglose
   * base/IVA **no** viaja: lo deriva el servidor (D-45).
   */
  unit_price: string;
}

/** Body de `POST /bills/checkout`. O `customer_id` o `new_customer`, nunca ambos. */
export interface ICheckoutPayload {
  customer_id?: string | null;
  new_customer?: { nit: string | null; fullname: string } | null;
  lines: ICheckoutLine[];
}

/** Lo que devuelve el checkout: la factura recién emitida. */
export interface ICheckoutResult {
  id: string;
  bill_number: string;
  subtotal: string;
  total_iva: string;
  total: string;
  fiscal_status: TFiscalStatus | null;
}

/**
 * Body de `POST /bills/{id}/void`. El motivo es obligatorio: un mes después,
 * "anulada" a secas no distingue un error de digitación de una devolución, y
 * son cosas distintas para el inventario.
 */
export interface IBillVoidPayload {
  reason: string;
}

/**
 * Respuesta de `GET /bills/export/summary` — cuenta qué entraría en el paquete
 * **sin construirlo** (D-78), para que el diálogo diga cuántas facturas son
 * antes de que el usuario confirme una descarga que arma un PDF por cada una.
 */
export interface IBillPackageSummary {
  business_name: string;
  platform_version: string;
  total_bills: number;
  /** Cuántas del corte están anuladas (D-60) — van marcadas en el paquete. */
  voided_bills: number;
  /**
   * Los dos los decide el backend, nunca el cliente: el día que entre
   * SQLCipher (D-06) o exista la copia firmada del proveedor DIAN
   * (D-09/D-38), pasan a `true` y las advertencias se apagan solas.
   */
  encrypted: boolean;
  dian_valid: boolean;
}

/** Query params que aceptan `GET /bills/` y `GET /bills/summary`. */
export interface IBillFilters {
  customer?: string;
  bill_number?: string;
  /** `YYYY-MM-DD`, inclusive. */
  date_from?: string;
  /** `YYYY-MM-DD`, inclusive — el servidor lo estira al final del día. */
  date_to?: string;
  fiscal_status?: TFiscalStatus;
  /**
   * Eje documento (D-81): omitir = todas, `false` = vigentes, `true` =
   * anuladas. Es el único estado que la pantalla filtra hoy — el fiscal sigue
   * aceptándose por API para cuando exista la integración DIAN.
   */
  voided?: boolean;
  /**
   * Exportar solo estas facturas (los checkboxes de la tabla). **Se combina**
   * con los demás filtros, no los reemplaza — y el `tenant_id` del token sigue
   * aplicando siempre, así que mandar ids de otro negocio devuelve vacío.
   * Solo lo aceptan los endpoints de exportación.
   */
  ids?: string[];
  skip?: number;
  limit?: number;
}
