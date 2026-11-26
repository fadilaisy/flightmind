import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // maplibre-gl finds its worker next to itself, so it must not be prebundled.
  optimizeDeps: { exclude: ["maplibre-gl"] },
  server: { host: "127.0.0.1", port: 5173 },
});
