// The ten end-to-end scenarios from the console spec, Section 9.
import { expect, test } from "@playwright/test";
import { ADMIN, apiGet, apiPost, dragCard, EXEC, lastEvent, OWNER, reset, signIn, writeRequests } from "./helpers";

test.beforeEach(async ({ request }) => reset(request));

test("1. moving review_gates to evaluation updates Portfolio and Flow without reload", async ({ page, request }) => {
  type Flow = { sankey: { source: string; target: string; value: number }[] };
  const before = (await apiGet<Flow>(request, "/flow?range=90")).sankey.find((l) => l.source === "review_gates" && l.target === "evaluation")?.value ?? 0;
  await signIn(page, ADMIN);
  await page.goto("/pipeline");
  await page.evaluate(() => ((window as unknown as { __sameDocument: boolean }).__sameDocument = true));
  await dragCard(page, "mortgage-doc-qa", "evaluation");
  await expect(page.getByTestId("announcer")).toContainText("moved to Evaluation");
  expect((await lastEvent(request, "mortgage-doc-qa")).source).toBe("drag");

  await page.getByRole("link", { name: "Flow" }).first().click();
  await page.getByRole("button", { name: "Show as table" }).first().click();
  await expect(page.getByRole("row", { name: new RegExp(`Review gates Evaluation ${before + 1}$`) })).toBeVisible();

  await page.getByRole("link", { name: "Portfolio" }).first().click();
  await page.getByRole("button", { name: "Table", exact: true }).click();
  await expect(page.getByRole("row", { name: /Mortgage Document Q&A/ })).toContainText("Evaluation");
  // A reload would have cleared this marker.
  expect(await page.evaluate(() => (window as unknown as { __sameDocument?: boolean }).__sameDocument)).toBe(true);
});

test("2. a second user's move shows the conflict drawer", async ({ page, request }) => {
  await signIn(page, ADMIN);
  await page.goto("/pipeline");
  await expect(page.locator('[data-app="policy-qa"]')).toBeVisible();
  const app = await apiGet<{ app: { version: number } }>(request, "/apps/policy-qa");
  const other = await apiPost(request, "/apps/policy-qa/move", { to_stage: "review_gates", expected_version: app.app.version, source: "api" });
  expect(other.ok()).toBeTruthy();
  await dragCard(page, "policy-qa", "review_gates");
  const drawer = page.getByTestId("conflict-drawer");
  await expect(drawer).toBeVisible();
  await expect(drawer.getByRole("button", { name: "Use server version" })).toBeVisible();
  await expect(drawer.getByRole("button", { name: "Review and retry" })).toBeVisible();
});

test("3. scheduling a review from Governance Assist updates the score and deadline", async ({ page }) => {
  await signIn(page, ADMIN);
  await page.goto("/portfolio?assist=1");
  const row = page.getByTestId("assist-row-it-ticket-summaries");
  const before = Number(await row.getByLabel(/^Score/).textContent());
  await row.getByRole("button", { name: "Schedule review" }).click();
  await row.getByLabel("Review date").fill("2026-10-15");
  await row.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByText("Review scheduled")).toBeVisible();
  await expect.poll(async () => Number(await page.getByTestId("assist-row-it-ticket-summaries").getByLabel(/^Score/).textContent())).toBeLessThan(before);
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("next-gate")).toContainText("Scheduled review");
  await expect(page.getByTestId("next-gate")).toContainText("IT Ticket Summaries");
});

test("4. a governance note leaves exactly one timeline entry after reload", async ({ page }) => {
  await signIn(page, OWNER);
  await page.goto("/apps?app=meeting-notes");
  const box = page.getByLabel("Governance note");
  await box.fill("Scope agreed with operations; pilot limited to one team.");
  await box.press("ControlOrMeta+Enter");
  await expect(page.getByText("Note saved")).toBeVisible();
  await page.reload();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("Scope agreed with operations")).toHaveCount(1);
  await expect(dialog.getByText("Note added", { exact: true })).toHaveCount(1);
});

test("5. the light theme swaps every token, persists, and refetches nothing", async ({ page }) => {
  await signIn(page, OWNER, "dark");
  await page.goto("/portfolio");
  await expect(page.locator("main")).toContainText("Apps in production");
  const token = () => page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--bg_canvas").trim().toUpperCase());
  expect(await token()).toBe("#0A0F1A");
  const fetched: string[] = [];
  page.on("request", (r) => r.url().includes("/api/") && !r.url().endsWith("/api/events") && fetched.push(r.url()));
  await page.getByRole("button", { name: "Switch to light theme" }).click();
  await expect.poll(token).toBe("#F6F8FB");
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--accent").trim().toUpperCase())).toBe("#1E6BD8");
  expect(fetched, `requests after toggling: ${fetched.join(", ")}`).toEqual([]);
  await page.reload();
  await expect(page.locator("main")).toContainText("Apps in production");
  await expect.poll(token).toBe("#F6F8FB");
});

test("6. a keyboard-only move produces the same audit event as a drag", async ({ page, request }) => {
  await signIn(page, ADMIN);
  await page.goto("/pipeline");
  const card = page.locator('[data-app="policy-qa"]');
  await card.focus();
  await page.keyboard.press("Space");
  await expect(page.getByTestId("announcer")).toContainText("Move mode");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("announcer")).toContainText("moved to Review gates");
  const keyboard = await lastEvent(request, "policy-qa");

  await dragCard(page, "procurement-intake", "review_gates");
  await expect(page.getByTestId("announcer")).toContainText("Procurement Intake moved to Review gates");
  const drag = await lastEvent(request, "procurement-intake");

  expect(keyboard.source).toBe("keyboard");
  expect(drag.source).toBe("drag");
  const shape = (e: typeof drag) => ({ kind: e.kind, actor: e.actor, from: e.from_stage, to: e.to_stage, keys: Object.keys(e).sort() });
  expect(shape(keyboard)).toEqual(shape(drag));
});

test("7. platform and date filters apply to every module", async ({ page }) => {
  await signIn(page, ADMIN);
  await page.goto("/portfolio");
  await page.getByLabel("Platform").first().selectOption("copilot");
  await page.getByLabel("Date range").selectOption("30");
  await expect(page).toHaveURL(/platform=copilot/);
  await expect(page).toHaveURL(/range=30/);
  const scope = "Copilot · last 30 days";
  await expect(page.locator("[data-band=portfolio]")).toContainText(scope);
  await expect(page.getByRole("region", { name: /apps are worth scaling/ })).toContainText(scope);
  await page.getByRole("region", { name: /carries the most spend/ }).getByRole("button", { name: "Show as table" }).click();
  await expect(page.getByRole("row", { name: /^Abacus 0/ })).toBeVisible();
  await page.getByRole("button", { name: "Table", exact: true }).click();
  const catalog = page.getByRole("table", { name: "Portfolio catalog" });
  await expect(catalog.locator("tbody tr").first()).toBeVisible();
  const platforms = await catalog.locator("tbody tr td:nth-child(4)").allTextContents();
  expect(platforms.length).toBeGreaterThan(0);
  expect(new Set(platforms)).toEqual(new Set(["Copilot"]));
});

test("8. a move with missing requirements is blocked and announced before any mutation", async ({ page }) => {
  await signIn(page, OWNER);
  await page.goto("/pipeline");
  const writes = writeRequests(page);
  await page.locator('[data-app="meeting-notes"]').focus();
  await page.keyboard.press("Space");
  await page.keyboard.press("ArrowRight");
  await expect(page.getByTestId("announcer")).toContainText("blocked");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("announcer")).toContainText("Blocked: Business case requires a business case");
  expect(writes).toEqual([]);
});

test("9. an executive viewer sees no write controls on any page", async ({ page }) => {
  await signIn(page, EXEC);
  const nav = page.getByRole("navigation", { name: "Main" }).first();
  for (const path of ["/portfolio", "/flow", "/portfolio?assist=1", "/portfolio?app=sales-email-drafts", "/settings"]) {
    await page.goto(path);
    await expect(page.locator("main")).not.toContainText("Loading");
    for (const label of ["Export CSV", "Export PDF", "Save note", "Schedule review", "Mark safe", "Approve", "Reject", "Dismiss"]) {
      await expect(page.getByRole("button", { name: label, exact: true })).toHaveCount(0);
    }
  }
  await expect(nav.getByRole("link", { name: "Pipeline" })).toHaveCount(0);
  await expect(nav.getByRole("link", { name: "Reviews" })).toHaveCount(0);
});

test("10. the snapshot loads with no backend and exposes no write endpoint", async ({ page }) => {
  const requests: { method: string; url: string }[] = [];
  page.on("request", (r) => requests.push({ method: r.method(), url: r.url() }));
  for (const route of ["#/portfolio", "#/pipeline", "#/flow", "#/apps/support-triage?tab=experiments", "#/incidents"]) {
    await page.goto(`http://127.0.0.1:8771/${route}`);
    await expect(page.getByRole("status").first()).toContainText("SNAPSHOT");
  }
  await expect(page.getByRole("button", { name: "Export CSV" })).toHaveCount(0);
  expect(requests.filter((r) => r.method !== "GET")).toEqual([]);
  expect(requests.filter((r) => r.url.includes("/api/"))).toEqual([]);
  expect(requests.every((r) => r.url.startsWith("http://127.0.0.1:8771/") || r.url.startsWith("data:"))).toBeTruthy();
});
