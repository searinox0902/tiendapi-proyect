import { http } from "@/lib/axios";
import type { IPage } from "@/api/references/references.types";
import type {
  IItemCreatePayload,
  IItemDetail,
  IItemRead,
  IItemStock,
  IItemStockFilters,
  IItemStockSummary,
  IItemUpdatePayload,
  IProductImportPreview,
  IProductImportResult,
  IProductImportUndoResult,
} from "./items.types";

export const itemsApi = {
  /** Existencias agregadas por Referencia — grilla de la pantalla Productos (D-51). */
  getStock(params: IItemStockFilters) {
    return http.get<IPage<IItemStock>>("/items/stock", { params });
  },

  /**
   * Cifras de cabecera de la pantalla Productos. Acepta los **mismos filtros**
   * que `getStock` a propósito: el resumen describe lo que se está mirando.
   */
  getStockSummary(params: IItemStockFilters) {
    return http.get<IItemStockSummary>("/items/stock/summary", { params });
  },

  /**
   * Cabecera + totales + **todas** las existencias de una Referencia.
   *
   * Sin paginar a propósito: son las unidades de un solo producto y el caso de
   * uso es buscar una puntual, que exige tenerlas todas. El servidor las trae
   * en una sola consulta con JOINs.
   */
  getDetailByReference(referenceId: string) {
    return http.get<IItemDetail>(`/items/by-reference/${referenceId}`);
  },

  /** Crea UNA unidad física (D-41). Un lote de N se resuelve llamando esto N veces. */
  createItem(payload: IItemCreatePayload) {
    return http.post<IItemRead>("/items/", payload);
  },

  /**
   * Actualización parcial de una unidad — mismo endpoint para dar de
   * baja/activar (`status`) y para reasignar proveedor/ubicación en lote (el
   * caller decide qué claves manda; las ausentes no se tocan).
   */
  updateItem(itemId: string, payload: IItemUpdatePayload) {
    return http.patch<IItemRead>(`/items/${itemId}`, payload);
  },

  /** Baja definitiva. El backend rechaza (409) si la unidad ya está facturada. */
  deleteItem(itemId: string) {
    return http.delete<void>(`/items/${itemId}`);
  },

  /**
   * Existencias como archivo descargable, y de paso la **plantilla** del
   * importador: un inventario vacío igual devuelve las columnas (D-73).
   * Una fila por grupo de unidades idénticas, no una por unidad.
   */
  exportProducts(format: "json" | "xlsx" | "markdown", params: IItemStockFilters = {}) {
    return http.get<Blob>("/items/export", {
      params: { format, ...params },
      responseType: "blob",
    });
  },

  /**
   * No escribe nada — cuenta qué haría `importProducts` con este mismo
   * archivo. Las cifras salen del mismo planificador que ejecuta el commit,
   * así que lo que promete es literalmente lo que va a pasar (A-30).
   *
   * El cliente no parsea nada: sube el archivo tal cual y el backend detecta
   * JSON vs. .xlsx — así el bundle del instalador Tauri no carga ninguna
   * librería de Excel (D-29/D-31).
   */
  previewProductImport(file: File, createMissing = true) {
    const formData = new FormData();
    formData.append("file", file);
    return http.post<IProductImportPreview>("/items/import/preview", formData, {
      params: { create_missing: createMissing },
    });
  },

  /**
   * `createMissing` decide qué pasa con un SKU que no está en el catálogo:
   * `true` (default) crea la Referencia y le cuelga las unidades en la misma
   * pasada; `false` marca esas filas como inválidas.
   */
  importProducts(file: File, createMissing = true) {
    const formData = new FormData();
    formData.append("file", file);
    return http.post<IProductImportResult>("/items/import", formData, {
      params: { create_missing: createMissing },
    });
  },

  /** Deshace el lote entero: unidades y el catálogo que ese archivo creó al pasar. */
  undoProductImportBatch(batchId: string) {
    return http.delete<IProductImportUndoResult>(`/items/import/${batchId}`);
  },
};
