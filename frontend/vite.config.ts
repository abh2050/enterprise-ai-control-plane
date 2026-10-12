import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// `npm run build:snapshot` builds a read-only static console against exported JSON.
// `npm run build:demo` builds the GitHub Pages console into ../console: the same static
// first paint plus the real backend running in the browser (src/lib/demo). Both use
// relative asset paths and need no server.
export default defineConfig(({ mode }) => {
  const snapshot = mode === "snapshot";
  const demo = mode === "demo";
  const flags: Record<string, string> = {};
  if (snapshot) flags["import.meta.env.VITE_SNAPSHOT"] = JSON.stringify("1");
  if (demo) flags["import.meta.env.VITE_DEMO"] = JSON.stringify("1");
  return {
    plugins: [react(), tailwindcss()],
    base: snapshot || demo ? "./" : "/",
    publicDir: snapshot ? ".snapshot-data" : demo ? ".demo-data" : "public",
    define: flags,
    worker: { format: "es" },
    build: {
      outDir: snapshot ? "dist-snapshot" : demo ? "../console" : "dist",
      emptyOutDir: true,
      target: "es2022",
    },
    server: { host: "127.0.0.1", proxy: { "/api": "http://127.0.0.1:8000" } },
  };
});
