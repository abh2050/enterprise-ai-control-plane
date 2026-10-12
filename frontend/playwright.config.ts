import { defineConfig, devices } from "@playwright/test";

// End-to-end scenarios and visual validation (console spec Section 9).
// The backend serves the built console on 8770 with fixture identity, the memory store,
// the SYNTHETIC seed, and a fixed clock. The snapshot site is plain static files on 8771,
// and the interactive demo on 8772.
export const FIXED_NOW = "2026-10-12T12:00:00+00:00";

export default defineConfig({
  testDir: "e2e",
  workers: 1,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  timeout: 60_000,
  expect: {
    toHaveScreenshot: { maxDiffPixelRatio: 0.005, threshold: 0.2, animations: "disabled" },
  },
  snapshotPathTemplate: "e2e/baselines/{arg}{ext}",
  use: { baseURL: "http://127.0.0.1:8770", ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
  webServer: [
    {
      command: `cd .. && STORE_BACKEND=memory PROVIDER_MODE=fixture IDENTITY_MODE=fixture FIXED_NOW=${FIXED_NOW} uv run cp serve --port 8770`,
      url: "http://127.0.0.1:8770/api/health",
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: "python3 -m http.server 8771 --bind 127.0.0.1 --directory dist-snapshot",
      url: "http://127.0.0.1:8771/index.html",
      reuseExistingServer: false,
    },
    {
      // The interactive demo (npm run build:demo), served as plain static files like Pages.
      command: "python3 -m http.server 8772 --bind 127.0.0.1 --directory ../console",
      url: "http://127.0.0.1:8772/index.html",
      reuseExistingServer: false,
    },
  ],
});
