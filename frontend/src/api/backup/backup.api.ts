import { http } from "@/lib/axios";
import type { IBackupSummary } from "./backup.types";

export const backupApi = {
  /** No construye el archivo — solo cuenta qué se llevaría (D-77). */
  getSummary() {
    return http.get<IBackupSummary>("/backup/summary");
  },

  /**
   * Descarga el proyecto completo como archivo SQLite. `responseType: "blob"`
   * es obligatorio: sin él axios trata el binario como texto y lo corrompe.
   * El alcance lo decide el token (tenant), nunca un parámetro del cliente.
   */
  exportProject() {
    return http.get<Blob>("/backup/export", { responseType: "blob" });
  },
};
