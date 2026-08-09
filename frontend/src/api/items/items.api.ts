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
};
