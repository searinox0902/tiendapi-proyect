import { ref } from "vue";
import { defineStore } from "pinia";
import type {
  ICategory,
  IProvider,
  IReference,
  IReferenceFilters,
  IReferenceSummary,
} from "@/api/references/references.types";
import { referencesApi } from "@/api/references/references.api";

export const useReferencesStore = defineStore("references", () => {

  const references = ref<IReference[]>([]);
  const categories = ref<ICategory[]>([]);
  const providers = ref<IProvider[]>([]);
  /** Filas que pasan el filtro, ignorando la página. Sin esto no se sabe cuántas páginas dibujar. */
  const total = ref(0);
  const isLoading = ref(false);
  /** Distingue "falló la carga" de "no hay resultados": son estados distintos en la tabla. */
  const hasError = ref(false);
  /** Agregados de las cards. `null` mientras no haya cargado o si falló. */
  const summary = ref<IReferenceSummary | null>(null);

  async function fetchReferences(filters: IReferenceFilters): Promise<void> {
    isLoading.value = true;
    hasError.value = false;
    try {
      const { data } = await referencesApi.getReferences(filters);
      references.value = data.items;
      total.value = data.total;
    } catch (error) {
      console.error("Fetch references failed:", error);
      hasError.value = true;
      references.value = [];
      total.value = 0;
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchSummary(): Promise<void> {
    try {
      const { data } = await referencesApi.getSummary();
      summary.value = data;
    } catch (error) {
      console.error("Fetch summary failed:", error);
      summary.value = null;
      throw error;
    }
  }

  async function fetchCategories(): Promise<void> {
    try {
      const { data } = await referencesApi.getCategories();
      categories.value = data;
    } catch (error) {
      console.error("Fetch categories failed:", error);
      categories.value = [];
      throw error;
    }
  }

  async function fetchProviders(): Promise<void> {
    try {
      const { data } = await referencesApi.getProviders();
      providers.value = data;
    } catch (error) {
      console.error("Fetch providers failed:", error);
      providers.value = [];
      throw error;
    }
  }

  /** El backend devuelve `category_id`; la tabla muestra el nombre. */
  function categoryName(categoryId: string | null): string {
    if (categoryId === null) {
      return "—";
    }
    return categories.value.find(category => category.id === categoryId)?.name ?? "—";
  }

  return {
    references, categories, providers, total, isLoading, hasError, summary,
    fetchReferences, fetchSummary, fetchCategories, fetchProviders, categoryName,
  };
});
