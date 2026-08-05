import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Puerto 5180 para no chocar con el frontend principal (5173).
export default defineConfig({
  plugins: [vue()],
  server: { port: 5180, open: false },
});
