import { http } from "@/lib/axios";
import type {
  ICategory,
  IPage,
  IReference,
  IReferenceFilters,
  IReferenceSummary,
} from "./references.types";

export const referencesApi = {
  getReferences(params: IReferenceFilters) {
    return http.get<IPage<IReference>>("/references/", { params });
  },

  getSummary(latest = 5) {
    return http.get<IReferenceSummary>("/references/summary", { params: { latest } });
  },

  getCategories() {
    return http.get<ICategory[]>("/categories/");
  },

  /**
   * Sube la imagen de una Referencia nombrada por SKU (D-58). Medida temporal
   * de desarrollo (D-40): en producción esto lo maneja el wrapper Tauri contra
   * `appDataDir`, no el backend central.
   */
  uploadImage(sku: string, file: Blob) {
    const formData = new FormData();
    formData.append("file", file, `${sku}.jpg`);
    return http.post<{ url: string }>(`/references/images/${encodeURIComponent(sku)}`, formData);
  },
};
