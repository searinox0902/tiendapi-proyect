import { http } from "@/lib/axios";
import type { IPage } from "@/api/references/references.types";
import type {
  IBill,
  IBillDetail,
  IBillFilters,
  IBillPackageSummary,
  IBillSummary,
  IBillVoidPayload,
  ICheckoutPayload,
  ICheckoutResult,
} from "./bills.types";

export const billsApi = {
  /** Listado paginado y filtrable — tabla de la pantalla Facturación (D-51). */
  getBills(params: IBillFilters) {
    return http.get<IPage<IBill>>("/bills/", { params });
  },

  /**
   * Cifras de cabecera. Acepta los **mismos filtros** que `getBills` a
   * propósito: el resumen describe lo que se está mirando, no el histórico.
   */
  getSummary(params: IBillFilters) {
    return http.get<IBillSummary>("/bills/summary", { params });
  },

  /**
   * Cierra la venta de la caja: el servidor resuelve qué unidades físicas se
   * venden, descuenta inventario, deriva base/IVA (D-45) y emite la factura,
   * todo en una transacción. Devuelve 409 si no alcanzan las existencias.
   */
  checkout(payload: ICheckoutPayload) {
    return http.post<ICheckoutResult>("/bills/checkout", payload);
  },

  /**
   * Factura completa — pantalla Ver Factura. `/detail` y no `GET /bills/{id}`
   * porque esa devuelve las líneas crudas: `item_id` sin SKU ni nombre, y una
   * fila por unidad física en vez de una por Referencia.
   */
  getDetail(billId: string) {
    return http.get<IBillDetail>(`/bills/${billId}/detail`);
  },

  /**
   * Anula la factura y devuelve su mercancía al inventario (D-60), en una sola
   * transacción del servidor. Responde 409 si ya estaba anulada o si la DIAN
   * la autorizó (ese caso se corrige con nota crédito, no anulando).
   */
  void(billId: string, payload: IBillVoidPayload) {
    return http.post<IBillDetail>(`/bills/${billId}/void`, payload);
  },

  /**
   * El PDF de una sola factura, sin zip. Mismo documento que el que viene
   * dentro del paquete (D-78) — lo genera el mismo renderizador del servidor,
   * no una segunda implementación.
   */
  downloadPdf(billId: string) {
    return http.get<Blob>(`/bills/${billId}/pdf`, { responseType: "blob" });
  },

  /**
   * No construye el paquete — solo cuenta qué entraría (D-78). Acepta los
   * **mismos filtros** que `getBills` para que el conteo describa exactamente
   * el corte que el usuario tiene en pantalla.
   */
  getExportSummary(params: IBillFilters) {
    return http.get<IBillPackageSummary>("/bills/export/summary", { params });
  },

  /**
   * Descarga el paquete de Facturación: zip con un PDF por factura + Excel
   * índice (D-78). `responseType: "blob"` es obligatorio — sin él axios trata
   * el binario como texto y corrompe el zip.
   *
   * No existe contraparte de importación y no va a existir: las facturas salen,
   * jamás entran (asimetría de D-73, integridad de D-07).
   */
  exportPackage(
    params: IBillFilters,
    onProgress?: (loaded: number, total?: number) => void,
  ) {
    return http.get<Blob>("/bills/export", {
      params,
      responseType: "blob",
      //  `total` llega solo si la respuesta trae `Content-Length` (el endpoint
      //  lo hace, porque devuelve bytes y no un stream). Cuando no llega, el
      //  llamador muestra progreso indeterminado en vez de inventar un
      //  porcentaje: el zip se arma completo en el servidor antes de mandar el
      //  primer byte, así que durante esa fase no hay progreso real que medir.
      onDownloadProgress: event => onProgress?.(event.loaded, event.total),
    });
  },
};
