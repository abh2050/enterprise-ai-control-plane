import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// `npm run build:snapshot` builds a read-only static console against exported JSON:
// relative asset paths for GitHub Pages and no backend.
export default defineConfig(({ mode }) => {
  const snapshot = mode === "snapshot";
  return {
    plugins: [react(), tailwindcss()],
    base: snapshot ? "./" : "/",
    publicDir: snapshot ? ".snapshot-data" : "public",
    define: snapshot ? { "import.meta.env.VITE_SNAPSHOT": JSON.stringify("1") } : {},
    build: { outDir: snapshot ? "dist-snapshot" : "dist", target: "es2022" },
    server: { host: "127.0.0.1", proxy: { "/api": "http://127.0.0.1:8000" } },
  };
});
