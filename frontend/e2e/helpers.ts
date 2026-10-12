import { expect, type APIRequestContext, type Page, type Request } from "@playwright/test";

export const API = "http://127.0.0.1:8770/api";
export const ADMIN = "admin@example.com";
export const OWNER = "owner@example.com";
export const EXEC = "exec@example.com";

export async function reset(request: APIRequestContext) {
  const r = await request.post(`${API}/fixture/reset`);
  expect(r.status()).toBe(204);
}

export async function signIn(page: Page, email: string, theme = "dark") {
  await page.addInitScript(
    ([e, t]) => {
      localStorage.setItem("cp.fixtureUser", e);
      if (!localStorage.getItem(`cp.theme.${e}`)) localStorage.setItem(`cp.theme.${e}`, t);
    },
    [email, theme],
  );
}

export async function apiGet<T>(request: APIRequestContext, path: string, email = ADMIN): Promise<T> {
  const r = await request.get(`${API}${path}`, { headers: { "X-Fixture-User": email } });
  expect(r.ok(), await r.text()).toBeTruthy();
  return (await r.json()) as T;
}

export async function apiPost(request: APIRequestContext, path: string, body: unknown, email = ADMIN) {
  return request.post(`${API}${path}`, { headers: { "X-Fixture-User": email }, data: body });
}

/** Drag a pipeline card to a stage column with real pointer events. */
export async function dragCard(page: Page, appId: string, stage: string) {
  const card = page.locator(`[data-app="${appId}"]`).first();
  const column = page.locator(`[data-stage="${stage}"]`);
  await card.scrollIntoViewIfNeeded();
  const from = (await card.boundingBox())!;
  await page.mouse.move(from.x + from.width / 2, from.y + 20);
  await page.mouse.down();
  await page.mouse.move(from.x + from.width / 2 + 10, from.y + 30, { steps: 4 });
  await column.scrollIntoViewIfNeeded();
  const to = (await column.boundingBox())!;
  await page.mouse.move(to.x + to.width / 2, to.y + 120, { steps: 12 });
  await page.mouse.up();
}

export function writeRequests(page: Page): Request[] {
  const seen: Request[] = [];
  page.on("request", (r) => {
    if (r.method() !== "GET" && !r.url().endsWith("/api/events")) seen.push(r);
  });
  return seen;
}

interface Event {
  kind: string;
  source?: string;
  actor: string;
  from_stage: string | null;
  to_stage: string | null;
}
export async function lastEvent(request: APIRequestContext, appId: string): Promise<Event> {
  const d = await apiGet<{ events: Event[] }>(request, `/apps/${appId}`);
  return d.events[d.events.length - 1]!;
}
