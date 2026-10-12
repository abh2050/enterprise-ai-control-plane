// Capture the deployed console (LIVE mode) for the M8 videos, before GCP teardown.
//
//   IAP_TOKEN=$(...) node scripts/capture_live.mjs SERVICE_URL OUT_DIR
//
// IAP admits the request through a self-signed service-account JWT sent as a bearer
// token (the same programmatic path as scripts/smoke_gcp.sh). Each page gets a 1080p
// screenshot per theme and a short screen recording with the data mode badge visible.
import { chromium } from "@playwright/test";
import { mkdirSync, renameSync } from "node:fs";
import { join } from "node:path";

const [url, out] = process.argv.slice(2);
const token = process.env.IAP_TOKEN;
if (!url || !out || !token) throw new Error("usage: IAP_TOKEN=... capture_live.mjs URL OUT_DIR");

const PAGES = [
  ["portfolio", "/portfolio"],
  ["pipeline", "/pipeline"],
  ["flow", "/flow"],
  ["applications", "/apps"],
  ["triage-business", "/apps/support-triage"],
  ["triage-experiments", "/apps/support-triage?tab=experiments"],
  ["triage-policy", "/apps/support-triage?tab=policy"],
  ["triage-shadow", "/apps/support-triage?tab=shadow"],
  ["triage-release", "/apps/support-triage?tab=release"],
  ["triage-monitoring", "/apps/support-triage?tab=monitoring"],
  ["reviews", "/reviews"],
  ["incidents", "/incidents"],
];

mkdirSync(join(out, "video"), { recursive: true });
const browser = await chromium.launch();
for (const theme of ["dark", "light"]) {
  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    colorScheme: theme,
    extraHTTPHeaders: { Authorization: `Bearer ${token}` },
    recordVideo: theme === "dark" ? { dir: join(out, "video"), size: { width: 1920, height: 1080 } } : undefined,
  });
  for (const [name, path] of PAGES) {
    const page = await ctx.newPage();
    await page.goto(url + path, { waitUntil: "networkidle", timeout: 90_000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: join(out, `${name}-${theme}.png`) });
    if (theme === "dark") {
      // Slow scroll so the recording shows the whole page.
      const h = await page.evaluate(() => document.documentElement.scrollHeight);
      for (let y = 0; y < h - 1080; y += 40) {
        await page.mouse.wheel(0, 40);
        await page.waitForTimeout(30);
      }
      await page.waitForTimeout(800);
    }
    const video = page.video();
    await page.close();
    if (video) renameSync(await video.path(), join(out, "video", `${name}.webm`));
    console.log(`captured ${name} (${theme})`);
  }
  await ctx.close();
}
await browser.close();
