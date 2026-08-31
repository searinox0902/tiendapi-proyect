import { http } from "@/lib/axios";
import type {
  IDirectoryImportPreview,
  IDirectoryImportResult,
  TDirectoryEntity,
  TDirectoryExportFormat,
} from "./directoryIO.types";

/**
 * Cliente genérico para `/directory/{entity}/export|import` (D-75) — mismo
 * contrato que `referencesApi.exportReferences`/`previewImport`/
 * `importReferences` (D-73/D-74), parametrizado por entidad en vez de un
 * cliente por cada una de las 5.
 */
export const directoryIOApi = {
  exportEntity(entity: TDirectoryEntity, format: TDirectoryExportFormat) {
    return http.get<Blob>(`/directory/${entity}/export`, {
      params: { format },
      responseType: "blob",
    });
  },

  previewImport(entity: TDirectoryEntity, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return http.post<IDirectoryImportPreview>(`/directory/${entity}/import/preview`, formData);
  },

  importEntity(entity: TDirectoryEntity, file: File, skipExisting = true) {
    const formData = new FormData();
    formData.append("file", file);
    return http.post<IDirectoryImportResult>(`/directory/${entity}/import`, formData, {
      params: { skip_existing: skipExisting },
    });
  },

  undoImportBatch(entity: TDirectoryEntity, batchId: string) {
    return http.delete<{ deleted: number }>(`/directory/${entity}/import/${batchId}`);
  },
};
