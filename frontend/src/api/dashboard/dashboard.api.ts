import { http } from "@/lib/axios";
import type { IDashboardRange, IDashboardSummary } from "./dashboard.types";

export const dashboardApi = {
  /**
   * Tablero operativo de producto (D-66) — un solo llamado para las cuatro
   * secciones. Van juntas porque comparten período y exclusiones (facturas
   * anuladas): partirlas invitaría a que una terminara filtrando distinto.
   *
   * El rango va en `from`/`to` (D-69). Ambos son opcionales del lado del
   * servidor —sin ellos responde los últimos 30 días— pero acá se mandan
   * siempre: la pantalla nunca está sin rango elegido.
   */
  getSummary(range: IDashboardRange) {
    return http.get<IDashboardSummary>("/dashboard/summary", { params: range });
  },
};
