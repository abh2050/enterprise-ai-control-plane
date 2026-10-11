import type { ReactNode } from "react";
import { Link } from "react-router";
import type { DatasetLabel, Metric, Provenance } from "../api";

const BADGE_STYLE: Record<Provenance | DatasetLabel, string> = {
  MEASURED: "border-ok/40 text-ok",
  SIMULATED: "border-accent/40 text-accent",
  FIXTURE: "border-warn/50 text-warn",
  ASSUMPTION: "border-muted/50 text-muted",
  SYNTHETIC: "border-warn/50 text-warn",
  AUTHORED: "border-muted/50 text-muted",
};

const BADGE_HELP: Record<Provenance | DatasetLabel, string> = {
  MEASURED: "Measured from real runs of this system",
  SIMULATED: "Computed from simulated traffic",
  FIXTURE: "Placeholder data for local development and demos",
  ASSUMPTION: "An assumed input, not a measurement",
  SYNTHETIC: "Generated sample data, not a real organization",
  AUTHORED: "Written by one person; single rater",
};

export function ProvenanceBadge({ label }: { label: Provenance | DatasetLabel }) {
  return (
    <span
      title={BADGE_HELP[label]}
      className={`inline-flex items-center rounded border px-1.5 py-px text-[10px] font-semibold tracking-wide ${BADGE_STYLE[label]}`}
    >
      {label}
    </span>
  );
}

function formatMetric(m: Metric): string {
  if (m.value === null) return "—";
  if (m.unit.startsWith("USD")) {
    return m.value.toLocaleString(undefined, {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    });
  }
  return m.value.toLocaleString();
}

/** The only way to put a number on screen. Requires a Metric, so provenance is mandatory. */
export function MetricTile({
  title,
  metric,
  to,
  hint,
}: {
  title: string;
  metric: Metric;
  to?: string;
  hint?: string;
}) {
  const body = (
    <>
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs text-muted">{title}</span>
        <ProvenanceBadge label={metric.provenance} />
      </div>
      <div className="mt-2 text-2xl font-semibold" title={`Source: ${metric.source}`}>
        {formatMetric(metric)}
      </div>
      <div className="mt-1 text-xs text-muted">{hint ?? metric.unit}</div>
    </>
  );
  const cls =
    "animate-enter block rounded-lg border border-line bg-surface p-4 transition-colors";
  return to ? (
    <Link to={to} className={`${cls} hover:border-accent`}>
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}

export function MetricValue({ metric }: { metric: Metric }) {
  return (
    <span className="inline-flex items-center gap-1.5" title={`Source: ${metric.source}`}>
      <span>{formatMetric(metric)}</span>
      <ProvenanceBadge label={metric.provenance} />
    </span>
  );
}

type Status = "green" | "amber" | "red";
const STATUS: Record<Status, { icon: string; text: string; cls: string }> = {
  green: { icon: "●", text: "Healthy", cls: "bg-ok-bg text-ok" },
  amber: { icon: "▲", text: "Needs attention", cls: "bg-warn-bg text-warn" },
  red: { icon: "■", text: "At risk", cls: "bg-bad-bg text-bad" },
};

/** Status is never color alone: each pill pairs a shape icon with a text label. */
export function StatusPill({ status, text }: { status: Status; text?: string }) {
  const s = STATUS[status];
  return (
    <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs ${s.cls}`}>
      <span aria-hidden="true">{s.icon}</span>
      {text ?? s.text}
    </span>
  );
}

export function EmptyState({
  title,
  missing,
  action,
}: {
  title: string;
  missing: string;
  action: string;
}) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-surface p-6">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted">
        <span className="font-medium text-ink">Missing: </span>
        {missing}
      </p>
      <p className="mt-1 text-sm text-muted">
        <span className="font-medium text-ink">How it fills: </span>
        {action}
      </p>
    </div>
  );
}

export function PageHeader({ title, summary }: { title: string; summary: string }) {
  return (
    <header className="mb-6">
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="mt-1 max-w-3xl text-sm text-muted">{summary}</p>
    </header>
  );
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="mb-3 text-sm font-semibold">{title}</h2>
      {children}
    </section>
  );
}

export function QueryError({ error }: { error: Error }) {
  const status = (error as { status?: number }).status;
  const message =
    status === 401
      ? "Choose an identity in the header to load this page."
      : status === 403
        ? "Your role cannot view this page."
        : `The API returned an error: ${error.message}`;
  return (
    <div role="alert" className="rounded-lg border border-line bg-surface p-4 text-sm text-muted">
      {message}
    </div>
  );
}

export function Loading() {
  return <div className="text-sm text-muted">Loading…</div>;
}
