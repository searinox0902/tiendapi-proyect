import { http } from "@/lib/axios";
import type {
  ICategory,
  IPage,
  IProvider,
  IReference,
  IReferenceCreate,
  IReferenceFilters,
  IReferenceSummary,
} from "./references.types";

export const referencesApi = {
  getReferences(params: IReferenceFilters) {
    return http.get<IPage<IReference>>("/references/", { params });
  },

  createReference(payload: IReferenceCreate) {
    return http.post<IReference>("/references/", payload);
  },

  updateReference(id: string, payload: IReferenceCreate) {
    return http.put<IReference>(`/references/${id}`, payload);
  },

  deleteReference(id: string) {
    return http.delete<void>(`/references/${id}`);
  },

  /** Autocompletado/verificación por SKU exacto (`GET /references/lookup`); `null` si no existe. */
  lookupReference(sku: string) {
    return http.get<IReference | null>("/references/lookup", { params: { sku } });
  },

  getSummary(latest = 5) {
    return http.get<IReferenceSummary>("/references/summary", { params: { latest } });
  },

  getCategories() {
    return http.get<ICategory[]>("/categories/");
  },

  getProviders() {
    return http.get<IProvider[]>("/providers/");
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
