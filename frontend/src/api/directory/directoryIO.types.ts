/** Entidades de soporte del Directorio con export/import genérico (D-75). */
export type TDirectoryEntity = "providers" | "locations" | "categories" | "customers" | "brands";

/**
 * Formatos de `GET /directory/{entity}/export`. El **JSON y el Excel son los
 * de intercambio** (round-trip fiel, D-74); Markdown es solo salida humana.
 */
export type TDirectoryExportFormat = "json" | "xlsx" | "markdown";

export interface IDirectoryImportInvalidRow {
  index: number;
  key_value: string | null;
  reason: string;
}

/** Respuesta de `POST /directory/{entity}/import/preview` — no escribe nada. */
export interface IDirectoryImportPreview {
  total_rows: number;
  new_count: number;
  existing_keys: string[];
  invalid: IDirectoryImportInvalidRow[];
}

/** Respuesta de `POST /directory/{entity}/import` — ya escribió en la BBDD. */
export interface IDirectoryImportResult {
  created: number;
  skipped: number;
  invalid: number;
  /** `null` si `created === 0`: no hay lote que deshacer. */
  batch_id: string | null;
}
