import { ref } from "vue";
import { defineStore } from "pinia";
import type {
  IItemDetail,
  IItemStock,
  IItemStockFilters,
  IItemStockSummary,
} from "@/api/items/items.types";
import { itemsApi } from "@/api/items/items.api";
import { ensureMinDuration } from "@/lib/async";

/** Localhost responde en pocos ms — sin este piso el skeleton de la grilla parpadea en vez de notarse. */
const SKELETON_MIN_DURATION_MS = 340;

export const useItemsStore = defineStore("items", () => {

  /** Tandas acumuladas de existencias agregadas por Referencia (no de `Item` sueltos) — scroll infinito, no una sola página. */
  const stock = ref<IItemStock[]>([]);
  /** Referencias que pasan el filtro, ignorando cuántas se han cargado. Sin esto no se sabe si queda más por traer. */
  const total = ref(0);
  /** Carga inicial o por cambio de filtros: reemplaza `stock` y dispara el estado de skeleton de la grilla completa. */
  const isLoading = ref(false);
  /** Carga de la siguiente tanda al llegar al final del scroll: agrega a `stock`, no reemplaza — no debe mostrar el skeleton de grilla completa. */
  const isLoadingMore = ref(false);
  /** Distingue "falló la carga" de "no hay resultados": son estados distintos en la grilla. */
  const hasError = ref(false);

  /**
   * `append: true` agrega la tanda al final (scroll infinito) en vez de
   * reemplazar `stock` — así una carga de "más" no pierde lo ya mostrado.
   */
  async function fetchStock(filters: IItemStockFilters, opts: { append?: boolean } = {}): Promise<void> {
    const append = opts.append ?? false;
    if (append) {
      isLoadingMore.value = true;
    } else {
      isLoading.value = true;
      hasError.value = false;
    }
    try {
      const { data } = await ensureMinDuration(itemsApi.getStock(filters), SKELETON_MIN_DURATION_MS);
      stock.value = append ? [...stock.value, ...data.items] : data.items;
      total.value = data.total;
    } catch (error) {
      console.error("Fetch stock failed:", error);
      if (!append) {
        hasError.value = true;
        stock.value = [];
        total.value = 0;
      }
      throw error;
    } finally {
      if (append) {
        isLoadingMore.value = false;
      } else {
        isLoading.value = false;
      }
    }
  }

  /** Producto abierto en la pantalla de aterrizaje. `null` mientras no ha cargado o si falló. */
  const detail = ref<IItemDetail | null>(null);
  const isLoadingDetail = ref(false);
  const hasDetailError = ref(false);

  async function fetchDetail(referenceId: string): Promise<void> {
    isLoadingDetail.value = true;
    hasDetailError.value = false;
    try {
      const { data } = await ensureMinDuration(
        itemsApi.getDetailByReference(referenceId),
        SKELETON_MIN_DURATION_MS,
      );
      detail.value = data;
    } catch (error) {
      console.error("Fetch item detail failed:", error);
      hasDetailError.value = true;
      detail.value = null;
      throw error;
    } finally {
      isLoadingDetail.value = false;
    }
  }

  /** Cifras de cabecera de la pantalla Productos. `null` mientras no ha cargado o si falló. */
  const summary = ref<IItemStockSummary | null>(null);
  const isLoadingSummary = ref(false);

  /**
   * Toma los mismos filtros que `fetchStock`: las cifras describen el conjunto
   * filtrado, así que se recalculan cuando el usuario cambia un filtro.
   * `skip`/`limit` no aplican — el servidor agrega sobre todo lo que pasa el
   * filtro, no sobre la tanda cargada.
   */
  async function fetchSummary(filters: IItemStockFilters): Promise<void> {
    isLoadingSummary.value = true;
    try {
      const { data } = await ensureMinDuration(
        itemsApi.getStockSummary(filters),
        SKELETON_MIN_DURATION_MS,
      );
      summary.value = data;
    } catch (error) {
      console.error("Fetch stock summary failed:", error);
      summary.value = null;
      throw error;
    } finally {
      isLoadingSummary.value = false;
    }
  }

  return {
    stock, total, isLoading, isLoadingMore, hasError, fetchStock,
    detail, isLoadingDetail, hasDetailError, fetchDetail,
    summary, isLoadingSummary, fetchSummary,
  };
});
