import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Dev server on 5173: the backend's default CORS list already allows http://localhost:5173 and http://127.0.0.1:5173.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173, strictPort: true },
  test: { environment: "jsdom", setupFiles: ["./tests/setup.js"], globals: true, css: false },
});
