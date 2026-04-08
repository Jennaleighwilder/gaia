import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Listen on all interfaces — default localhost-only can bind ::1 on Linux while Playwright
  // probes http://127.0.0.1:5173, so the webServer never goes ready. host: true fixes CI e2e.
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8090",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.js",
    exclude: ["**/node_modules/**", "**/e2e/**", "**/dist/**"],
  },
});
