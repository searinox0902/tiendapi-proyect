import axios from "axios";
import { useAuthStore } from "@/stores/auth";

export const http = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL}/api/v1`,
});

http.interceptors.request.use((config) => {
  const { token } = useAuthStore();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      useAuthStore().logout();

      // Sin esto te quedas dentro de una pantalla protegida y sin sesión: el
      // guard de rutas solo corre al navegar, no cuando el token vence estando
      // ya dentro. El import es dinámico para no cerrar el ciclo
      // axios → router → store → axios al cargar los módulos.
      const { default: router } = await import("@/router");
      if (router.currentRoute.value.name !== "login") {
        router.push({ name: "login" });
      }
    }
    return Promise.reject(error);
  }
);

if (import.meta.env.DEV) {
  const fakeLatencyMs = Number(import.meta.env.VITE_FAKE_LATENCY_MS ?? 0);
  if (fakeLatencyMs > 0) {
    http.interceptors.request.use(
      (config) =>
        new Promise((resolve) => setTimeout(() => resolve(config), fakeLatencyMs))
    );
  }
}
