// Typed client for the control plane API.
// Snapshot mode (VITE_SNAPSHOT=1) reads exported JSON files and refuses every write.

export type Provenance = "MEASURED" | "SIMULATED" | "FIXTURE" | "ASSUMPTION";
export type DatasetLabel = "SYNTHETIC" | "AUTHORED" | "IMPORTED";
export type Role = "app_owner" | "reviewer" | "governance_admin" | "executive_viewer";
export type Platform = "abacus" | "copilot" | "custom" | "managed";
export type Health = "healthy" | "warning" | "danger";

export const STAGES = [
  "intake",
  "business_case",
  "review_gates",
  "evaluation",
  "shadow",
  "controlled_activation",
  "monitored",
  "paused",
  "retired",
] as const;
export type Stage = (typeof STAGES)[number];
export const PLATFORMS: Platform[] = ["abacus", "copilot", "custom", "managed"];

export interface Metric {
  value: number | null;
  unit: string;
  provenance: Provenance;
  source: string;
}

export interface ModeInfo {
  data_mode: "LIVE" | "SIMULATED" | "FIXTURE";
  identity_mode: string;
  provider_mode: string;
  store_backend: string;
  dataset_labels: DatasetLabel[];
}

export interface Me {
  email: string;
  role: Role;
  permissions: string[];
  security_reviewer: boolean;
}

export interface AppCard {
  app_id: string;
  name: string;
  owner: string | null;
  business_unit: string;
  platform: Platform;
  stage: Stage;
  risk_tier: "low" | "medium" | "high";
  version: number;
  business_problem: string;
  days_in_stage: Metric;
  stall_warning: boolean;
  stalled_vs_median: boolean;
  monthly_spend_usd: Metric;
  monthly_budget_usd: number;
  estimated_value_usd: Metric;
  usage_series: number[];
  health: Health;
  health_rule: string;
  last_decision: string | null;
  last_activity_at: string | null;
  next_gate: { kind: string; due_at: string } | null;
  assist_score: number;
  assist_flagged: boolean;
  pending_gates: string[];
  submitted_by: string | null;
  provenance: string;
}

export interface MatrixPoint {
  app_id: string;
  name: string;
  risk_tier: "low" | "medium" | "high";
  cost: number;
  value: number | null;
  volume: number;
  stage: Stage;
  quadrant?: "Scale" | "Fix" | "Watch" | "Retire";
}

export interface PortfolioData {
  generated_at: string;
  filters: { platform: string | null; range_days: number };
  kpis: Record<"apps_in_production" | "monthly_model_spend_usd" | "imported_spend_usd" | "value_at_risk_usd", Metric>;
  assist: { flagged_count: number; top_reason: string | null; scored_at: string | null; threshold: number };
  secondary: Record<
    "total_apps" | "stalled_apps" | "estimated_monthly_value_usd" | "open_incidents" | "approvals_waiting",
    Metric
  >;
  matrix: {
    points: MatrixPoint[];
    needs_business_case: MatrixPoint[];
    cost_split: number;
    value_split: number;
    provenance: { cost: Provenance; value: Provenance };
  };
  attention: {
    app_id: string;
    name: string;
    stage: Stage;
    score: number;
    reason: string | null;
    evidence: string | null;
    action: string | null;
  }[];
  platforms: { platform: Platform; apps: number; spend: number }[];
  next_gate: { app_id: string; name: string; kind: string; due_at: string } | null;
  incident_open: boolean;
}

export interface AppEvent {
  event_id: string;
  app_id: string;
  kind: string;
  from_stage: Stage | null;
  to_stage: Stage | null;
  actor: string;
  reason: string;
  evidence_refs: string[];
  created_at: string;
}

export interface Note {
  note_id: string;
  app_id: string;
  author: string;
  text: string;
  created_at: string;
  edited_at: string | null;
  history: { text: string; until: string }[];
}

export interface AssistReason {
  code: string;
  points: number;
  label: string;
  action: string;
  evidence: string;
}

export interface AppDetailData {
  app: Record<string, unknown> & {
    app_id: string;
    name: string;
    stage: Stage;
    version: number;
    platform: Platform;
    business_problem: string;
    business_case: Record<string, { value?: number; unit?: string; justification?: string } | string> | null;
    gates: Record<string, { approved_by: string; approved_at: string; expires_at: string }>;
    prior_stage: Stage | null;
  };
  card: AppCard;
  events: AppEvent[];
  incidents: Incident[];
  assist: { score: number; reasons: AssistReason[]; scored_at: string } | null;
  notes: Note[];
  allowed_moves: Record<string, { allowed: boolean; code: string | null; message: string | null; needs_reason: boolean }>;
  external: boolean;
}

export interface Incident {
  incident_id: string;
  app_id: string;
  signal: string;
  threshold: number;
  observed: number;
  status: "open" | "mitigated" | "closed";
  actions: string[];
  opened_at: string;
  closed_at: string | null;
  provenance: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body: Record<string, unknown> = {},
  ) {
    super(message);
  }
  get code(): string | undefined {
    return this.body.code as string | undefined;
  }
}

export const SNAPSHOT = import.meta.env.VITE_SNAPSHOT === "1";
const IDENTITY_KEY = "cp.fixtureUser";

export function getFixtureUser(): string | null {
  try {
    return localStorage.getItem(IDENTITY_KEY);
  } catch {
    return null;
  }
}

export function setFixtureUser(email: string | null): void {
  try {
    if (email) localStorage.setItem(IDENTITY_KEY, email);
    else localStorage.removeItem(IDENTITY_KEY);
  } catch {
    // identity then lasts for this page view only
  }
}

/** File name for an exported snapshot response. */
export function snapshotFile(path: string): string {
  return `snapshot/${path.replace(/^\//, "").replace(/[/?=&]/g, "_") || "root"}.json`;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  if (SNAPSHOT) {
    if (method !== "GET") throw new ApiError(403, "The snapshot is read only");
    const res = await fetch(`${import.meta.env.BASE_URL}${snapshotFile(path)}`);
    if (!res.ok) throw new ApiError(res.status, "Not included in the snapshot");
    return (await res.json()) as T;
  }
  const headers: Record<string, string> = { Accept: "application/json" };
  const user = getFixtureUser();
  if (user) headers["X-Fixture-User"] = user;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(`/api${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  if (res.status === 204) return undefined as T;
  let data: Record<string, unknown> = {};
  try {
    data = (await res.json()) as Record<string, unknown>;
  } catch {
    // non-JSON body
  }
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : res.statusText;
    throw new ApiError(res.status, detail, data);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
};

export function query(params: Record<string, string | number | null | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== null && v !== undefined && v !== "") q.set(k, String(v));
  const s = q.toString();
  return s ? `?${s}` : "";
}
