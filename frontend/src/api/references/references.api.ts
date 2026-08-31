import { http } from "@/lib/axios";
import type {
  ICategory,
  IPage,
  IProvider,
  IReference,
  IReferenceCreate,
  IReferenceFilters,
  IReferenceImportPreview,
  IReferenceImportResult,
  IReferenceSummary,
  IReferenceVariantInfo,
  TExportFormat,
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

  /** Estado del grupo de variantes de un SKU (D-90): si existe, cuántas hay y qué código sigue. */
  getVariantInfo(sku: string) {
    return http.get<IReferenceVariantInfo>("/references/variants", { params: { sku } });
  },

  getSummary(latest = 5) {
    return http.get<IReferenceSummary>("/references/summary", { params: { latest } });
  },

  /**
   * Descarga el catálogo como archivo (D-73). Los tres formatos los genera el
   * backend —no el cliente— para que no puedan divergir en columnas, y porque
   * el .xlsx exige una librería que no queremos dentro del bundle que viaja en
   * el instalador Tauri (D-29/D-31).
   *
   * `filters` vacío = catálogo completo; con filtros = lo que el usuario ve.
   * `responseType: "blob"` es obligatorio: sin él axios interpreta el .xlsx
   * como texto y lo corrompe al llegar.
   */
  exportReferences(format: TExportFormat, filters: IReferenceFilters = {}) {
    return http.get<Blob>("/references/export", {
      params: { format, ...filters },
      responseType: "blob",
    });
  },

  /**
   * No escribe nada — solo cuenta qué haría `importReferences` con este mismo
   * archivo. Acepta JSON o el .xlsx exportado por el propio sistema (D-74); el
   * cliente no parsea nada, sube el archivo tal cual y el backend detecta el
   * formato — mismo motivo que el .xlsx de exportación: no queremos lógica de
   * formato de archivo en el bundle que viaja en el instalador Tauri.
   */
  previewImport(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return http.post<IReferenceImportPreview>("/references/import/preview", formData);
  },

  /**
   * `skipExisting` decide qué pasa con un SKU que ya existe (D-73, unicidad
   * blanda): `true` (default) lo salta, `false` lo trae igual como duplicado
   * — el usuario resuelve cuál se queda desde la pantalla de Referencias.
   */
  importReferences(file: File, skipExisting = true) {
    const formData = new FormData();
    formData.append("file", file);
    return http.post<IReferenceImportResult>("/references/import", formData, {
      params: { skip_existing: skipExisting },
    });
  },

  undoImportBatch(batchId: string) {
    return http.delete<{ deleted: number }>(`/references/import/${batchId}`);
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
