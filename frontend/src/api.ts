// Typed client for the control plane API. Mirrors backend/control_plane/contracts.py.

export type Provenance = "MEASURED" | "SIMULATED" | "FIXTURE" | "ASSUMPTION";
export type DatasetLabel = "SYNTHETIC" | "AUTHORED";
export type DataMode = "LIVE" | "SIMULATED" | "FIXTURE";
export type Role = "app_owner" | "reviewer" | "governance_admin" | "executive_viewer";
export type Platform = "abacus" | "copilot" | "custom" | "managed";
export type RiskTier = "low" | "medium" | "high";

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

/** A number that may be shown to a person. It cannot exist without provenance. */
export interface Metric {
  value: number | null;
  unit: string;
  provenance: Provenance;
  source: string;
}

export interface ModeInfo {
  data_mode: DataMode;
  identity_mode: string;
  provider_mode: string;
  store_backend: string;
  dataset_labels: DatasetLabel[];
}

export interface Me {
  email: string;
  role: Role;
}

export interface PortfolioSummary {
  total_apps: Metric;
  apps_in_production: Metric;
  apps_stalled: Metric;
  monthly_model_spend_usd: Metric;
  estimated_monthly_value_usd: Metric;
  open_incidents: Metric;
  approvals_waiting: Metric;
  apps_by_stage: Record<Stage, Metric>;
}

export interface AppCard {
  app_id: string;
  name: string;
  owner: string | null;
  business_unit: string;
  platform: Platform;
  stage: Stage;
  risk_tier: RiskTier;
  days_in_stage: Metric;
  monthly_spend_usd: Metric;
  provenance: Provenance | DatasetLabel;
}

export interface AppDetail {
  app_id: string;
  name: string;
  owner: string | null;
  business_unit: string;
  platform: Platform;
  business_problem: string;
  risk_tier: RiskTier;
  stage: Stage;
  paused: boolean;
  provenance: Provenance | DatasetLabel;
}

export interface AppEvent {
  event_id: string;
  kind: string;
  from_stage: Stage | null;
  to_stage: Stage | null;
  actor: string;
  reason: string;
  evidence_refs: string[];
  created_at: string;
}

export interface Incident {
  incident_id: string;
  app_id: string;
  signal: string;
  status: "open" | "mitigated" | "closed";
  opened_at: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

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
    // Storage can be unavailable; identity then lasts only for this page view.
  }
}

export async function get<T>(path: string): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const user = getFixtureUser();
  if (user) headers["X-Fixture-User"] = user;
  const res = await fetch(`/api${path}`, { headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = ((await res.json()) as { detail?: string }).detail ?? detail;
    } catch {
      // keep status text
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export const label = (s: string): string =>
  s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
