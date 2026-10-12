// Visual validation (console spec Section 9): 1440 x 900, 100% zoom, fixed seed and clock,
// both themes, at most 0.5% of pixels different. Charts are masked; antialiasing is
// absorbed by the per-pixel threshold. Baselines are owner-approved project screens.
import { expect, test } from "@playwright/test";
import { FIXED_NOW } from "../playwright.config";

test.setTimeout(60_000);
import { ADMIN, reset, signIn } from "./helpers";

const PAGES: [string, string][] = [
  ["portfolio", "/portfolio"],
  ["pipeline", "/pipeline"],
  ["flow", "/flow"],
  ["applications", "/apps"],
  ["release", "/apps/support-triage?tab=release"],
  ["reviews", "/reviews"],
  ["incidents", "/incidents"],
];

for (const theme of ["dark", "light"]) {
  for (const [name, path] of PAGES) {
    test(`visual ${name} ${theme}`, async ({ page, request }) => {
      await reset(request);
      // Pin the console's display clock (not the browser clock, which stalls rendering).
      await page.addInitScript((at) => localStorage.setItem("cp.displayClock", at), FIXED_NOW);
      await signIn(page, ADMIN, theme);
      await page.goto(path);
      // Wait for content, not for network idle: background polling keeps the network busy.
      await expect(page.locator("main h1").first()).toBeVisible();
      await expect(page.locator(".skeleton")).toHaveCount(0, { timeout: 15_000 });
      await page.evaluate(() => document.fonts.ready);
      await expect(page).toHaveScreenshot(`${name}-${theme}.png`, {
        mask: [page.locator(".recharts-wrapper"), page.locator("svg[role=img]")],
      });
    });
  }
}
