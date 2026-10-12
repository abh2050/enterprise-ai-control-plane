// The interactive demo (GitHub Pages build in ../console): the real backend runs in the
// page's worker. These checks run against plain static files, as GitHub Pages serves them.
import { expect, test, type Page } from "@playwright/test";
import { dragCard } from "./helpers";

const DEMO = "http://127.0.0.1:8772/";

async function open(page: Page, route: string, as = "admin@example.com") {
  await page.addInitScript((e) => {
    if (!sessionStorage.getItem("cp.demoTest")) {
      localStorage.setItem("cp.fixtureUser", e);
      sessionStorage.setItem("cp.demoTest", "1");
    }
  }, as);
  await page.goto(`${DEMO}#${route}`);
  await expect(page.getByText("The real backend runs in this tab")).toBeVisible({ timeout: 60_000 });
}

async function viewAs(page: Page, email: string) {
  await page.getByLabel("Viewing as").selectOption(email);
}

/** Every request that leaves the page. Writes must never appear: they stay in the worker. */
function outbound(page: Page): string[] {
  const seen: string[] = [];
  page.on("request", (r) => {
    if (r.method() !== "GET") seen.push(`${r.method()} ${r.url()}`);
  });
  return seen;
}

test("the page paints from static data before the engine is ready", async ({ page }) => {
  await page.goto(`${DEMO}#/portfolio`);
  await expect(page.getByText("Apps in production")).toBeVisible({ timeout: 5_000 });
  await expect(page.getByText("The real backend runs in this tab")).toBeVisible({ timeout: 60_000 });
});

test("a legal move succeeds, an illegal one is refused, and nothing leaves the browser", async ({ page }) => {
  const sent = outbound(page);
  await open(page, "/pipeline");
  await dragCard(page, "mortgage-doc-qa", "evaluation");
  await expect(page.getByTestId("announcer")).toContainText("moved to Evaluation");

  await page.locator('[data-app="meeting-notes"]').focus();
  await page.keyboard.press("Space");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("announcer")).toContainText("Blocked: Business case requires a business case");
  expect(sent).toEqual([]);
});

test("the submitter cannot approve their own gate", async ({ page }) => {
  await open(page, "/pipeline");
  await dragCard(page, "policy-qa", "review_gates");
  await expect(page.getByTestId("announcer")).toContainText("moved to Review gates");
  await page.goto(`${DEMO}#/reviews`);
  const card = page.getByRole("heading", { name: "Policy Q&A: Governance review" }).locator("xpath=ancestor::*[.//button][1]");
  await expect(card).toContainText("A different person must approve");
  await expect(card.getByRole("button", { name: "Approve" })).toBeDisabled();
});

test("a release proposed by the owner can be withheld but not fully activated", async ({ page }) => {
  await open(page, "/apps/support-triage?tab=policy", "owner@example.com");
  await page.getByRole("button", { name: "Propose release with this cohort" }).click();
  await expect(page.getByText(/^Proposed rel_/)).toBeVisible();
  await viewAs(page, "admin@example.com");
  await page.goto(`${DEMO}#/apps/support-triage?tab=release`);
  const form = page.locator("form").filter({ hasText: "Record the decision" }).first();
  await form.getByLabel("Decision").selectOption("activate_full");
  await expect(form.getByText("This decision is blocked because its gates fail")).toBeVisible();
  await form.getByLabel("Decision").selectOption("withhold");
  await form.getByRole("textbox").fill("Macro F1 is still below the floor on the frozen set.");
  await form.getByRole("button", { name: "Record decision" }).click();
  await expect(page.getByText("Decision recorded: Withhold")).toBeVisible();
});

test("an executive viewer gets no write controls", async ({ page }) => {
  await open(page, "/portfolio", "exec@example.com");
  for (const label of ["Export CSV", "Export PDF", "Approve", "Reject"]) {
    await expect(page.getByRole("button", { name: label, exact: true })).toHaveCount(0);
  }
  await expect(page.getByRole("navigation", { name: "Main" }).first().getByRole("link", { name: "Pipeline" })).toHaveCount(0);
});

test("reset restores the starting data", async ({ page }) => {
  await open(page, "/pipeline");
  await dragCard(page, "mortgage-doc-qa", "evaluation");
  await expect(page.getByTestId("announcer")).toContainText("moved to Evaluation");
  await page.getByRole("button", { name: "Reset demo" }).click();
  await expect(page.getByText("Demo reset to the starting data.")).toBeVisible();
  await expect(page.locator('[data-stage="review_gates"] [data-app="mortgage-doc-qa"]')).toBeVisible();
});
