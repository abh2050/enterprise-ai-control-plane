import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router";
import { get, label, type AppDetail as App, type AppEvent } from "../api";
import { EmptyState, Loading, PageHeader, ProvenanceBadge, QueryError } from "../components/ui";

const TABS = [
  { id: "business", label: "Business Case", milestone: "M3", what: "Assumptions, breakeven precision, and the sensitivity table." },
  { id: "experiments", label: "Experiments", milestone: "M2 and M3", what: "Side-by-side comparison of the three configs with bootstrap intervals." },
  { id: "policy", label: "Decision Policy", milestone: "M3 and M5", what: "Frozen thresholds, sensitive intents, and the cohort editor." },
  { id: "shadow", label: "Shadow", milestone: "M5", what: "Daily agreement, cost, and route comparisons (SIMULATED)." },
  { id: "release", label: "Release", milestone: "M5", what: "Gate results with thresholds and observed values, and the decision form." },
  { id: "monitoring", label: "Monitoring", milestone: "M5", what: "Daily signal charts with alert lines." },
  { id: "audit", label: "Audit", milestone: "", what: "" },
] as const;

type TabId = (typeof TABS)[number]["id"];

function Audit({ appId }: { appId: string }) {
  const events = useQuery({
    queryKey: ["events", appId],
    queryFn: () => get<AppEvent[]>(`/apps/${appId}/events`),
  });
  if (events.error) return <QueryError error={events.error} />;
  if (!events.data) return <Loading />;
  if (events.data.length === 0)
    return (
      <EmptyState
        title="No events recorded"
        missing="Lifecycle events for this app."
        action="Every stage transition writes an append-only event with actor, reason, and evidence (M4)."
      />
    );
  return (
    <ol className="space-y-2">
      {events.data.map((e) => (
        <li key={e.event_id} className="rounded border border-line bg-surface p-3 text-sm">
          <div className="font-medium">{label(e.kind)}</div>
          <div className="text-xs text-muted">
            {e.actor} · {new Date(e.created_at).toLocaleString()} · {e.reason}
          </div>
        </li>
      ))}
    </ol>
  );
}

export default function AppDetail() {
  const { appId = "" } = useParams();
  const [tab, setTab] = useState<TabId>("business");
  const app = useQuery({ queryKey: ["app", appId], queryFn: () => get<App>(`/apps/${appId}`) });

  if (app.error) return <QueryError error={app.error} />;
  if (!app.data) return <Loading />;
  const a = app.data;
  const current = TABS.find((t) => t.id === tab)!;

  return (
    <>
      <PageHeader title={a.name} summary={a.business_problem} />
      <dl className="mb-6 flex flex-wrap gap-x-8 gap-y-2 text-sm">
        {[
          ["Owner", a.owner ?? "No owner"],
          ["Business unit", a.business_unit],
          ["Platform", label(a.platform)],
          ["Stage", label(a.stage)],
          ["Risk tier", label(a.risk_tier)],
        ].map(([k, v]) => (
          <div key={k}>
            <dt className="text-xs text-muted">{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
        <div>
          <dt className="text-xs text-muted">Data</dt>
          <dd>
            <ProvenanceBadge label={a.provenance} />
          </dd>
        </div>
      </dl>

      <div role="tablist" aria-label="App detail" className="mb-4 flex gap-1 overflow-x-auto border-b border-line">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm ${
              tab === t.id ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div role="tabpanel">
        {tab === "audit" ? (
          <Audit appId={appId} />
        ) : (
          <EmptyState
            title={`${current.label} has no evidence yet`}
            missing={current.what}
            action={`This tab fills from real runs in ${current.milestone}.`}
          />
        )}
      </div>
    </>
  );
}
