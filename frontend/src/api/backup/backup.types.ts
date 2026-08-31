/** Conteo de una tabla dentro del respaldo, ya con etiqueta legible. */
export interface IBackupTableCount {
  table: string;
  label: string;
  count: number;
}

/**
 * Respuesta de `GET /backup/summary` — cuenta qué entraría en el respaldo
 * **sin construir el archivo** (D-77), para que el diálogo muestre el alcance
 * real antes de confirmar la descarga.
 */
export interface IBackupSummary {
  business_name: string;
  platform_version: string;
  /**
   * `false` mientras SQLCipher (D-06) no esté implementado: el archivo sale
   * en claro. Lo decide el backend, no el cliente — el día que se cifre, la
   * advertencia de la UI se apaga sola sin tocar el frontend.
   */
  encrypted: boolean;
  counts: IBackupTableCount[];
}
