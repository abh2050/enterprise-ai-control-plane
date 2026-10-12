// App Detail (console spec Section 9). Support Triage tabs read real evidence from
// artifacts/experiment_summary.json; release decisions, shadow, and monitoring arrive in M5.
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, OctagonAlert } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { useSession } from "../components/Shell";
import { Card, DataTable, EmptyState, HeaderBand, HealthPill, Input, MetricInline, ModuleError, ProvenanceBadge, Select, Skeleton, StatusText, cx } from "../components/ui";
import { api, type AppDetailData, type Metric } from "../lib/api";
import { label, money, pct, relative, timestamp } from "../lib/format";
import { useUrlFilters } from "../lib/state";
import { CohortEditor, MonitoringTab, ReleaseTab, ShadowTab } from "./detail/M5Tabs";

interface ConfigEvidence {
  experiment_id: string;
  model_id: string;
  policy: { policy_id: string; thresholds: Record<string, number>; sensitive_intents: string[]; eligible_cohort: string[]; tuning: Record<string, unknown>; created_at: string };
  scorecard: Record<string, Metric>;
  usage: Record<string, number> | null;
  per_intent: { intent: string; support: number; recall: number | null; precision: number | null; auto_rate: number | null; sensitive: boolean }[];
  sensitive_confusion: { intent: string; cases: number; predicted: Record<string, number>; routes: Record<string, number> }[];
  economics: {
    rates: Record<string, number>;
    breakeven_precision: number | null;
    gate_threshold: number | null;
    net_monthly: Record<string, number>;
    total_cost_per_correct_usd: number | null;
    sensitivity: { misroute_cost_standard: number; review_minutes: number; net_monthly_value: number; breakeven_precision: number | null }[];
  };
  source: string;
}
interface Evidence {
  available: boolean;
  configs: Record<string, ConfigEvidence>;
  bootstrap: { candidate: string; baseline: string; metric: string; delta: number | null; ci_low: number | null; ci_high: number | null }[];
  assumptions: Record<string, { value: number; unit: string; justification: string }>;
  sensitivity_grid: { misroute_cost_standard: number[]; review_minutes: number[] };
}

const ALL_TABS = [
  { id: "business", label: "Business Case" },
  { id: "experiments", label: "Experiments" },
  { id: "policy", label: "Decision Policy" },
  { id: "shadow", label: "Shadow" },
  { id: "release", label: "Release" },
  { id: "monitoring", label: "Monitoring" },
  { id: "audit", label: "Audit" },
] as const;
type TabId = (typeof ALL_TABS)[number]["id"];

const CONFIG_LABEL: Record<string, string> = {
  classifier_v1: "Classifier",
  llm_low_cost_v1: "Gemini 3.1 Flash-Lite",
  llm_high_capability_v1: "Gemini 3.8 Flash",
};
const ORDER = ["classifier_v1", "llm_low_cost_v1", "llm_high_capability_v1"];

function m(card: Record<string, Metric>, key: string) {
  return card[key] ? <MetricInline metric={card[key]!} /> : "—";
}

function BusinessCase({ d, ev }: { d: AppDetailData; ev: Evidence | undefined }) {
  const [config, setConfig] = useState("llm_high_capability_v1");
  const own = d.app.business_case;
  return (
    <div className="flex flex-col gap-6">
      <Card title="Problem statement">
        <p className="t-body">{d.app.business_problem}</p>
      </Card>
      {ev?.available ? (
        <>
          <Card title="Assumptions behind every money figure" action={<ProvenanceBadge label="ASSUMPTION" />}>
            <DataTable caption="Business model assumptions" columns={["Input", "Value", "Justification"]} rows={Object.entries(ev.assumptions).map(([k, a]) => [label(k), `${a.value.toLocaleString()} ${a.unit}`, a.justification])} />
          </Card>
          <Card title="Breakeven precision: below it, automation loses money">
            <DataTable
              caption="Breakeven by config"
              columns={["Config", "Auto precision (MEASURED)", "Breakeven (ASSUMPTION)", "Gate: breakeven + 0.03", "Net monthly value (ASSUMPTION)"]}
              rows={ORDER.filter((c) => ev.configs[c]).map((c) => {
                const e = ev.configs[c]!.economics;
                const pass = e.gate_threshold !== null && e.rates.auto_precision! >= e.gate_threshold;
                return [
                  CONFIG_LABEL[c],
                  e.rates.auto_precision!.toFixed(3),
                  e.breakeven_precision?.toFixed(3) ?? "—",
                  pass ? (
                    <StatusText key="g" tone="healthy" icon={CheckCircle2}>
                      Pass ({e.gate_threshold?.toFixed(3)})
                    </StatusText>
                  ) : (
                    <StatusText key="g" tone="danger" icon={OctagonAlert}>
                      Fail ({e.gate_threshold?.toFixed(3)})
                    </StatusText>
                  ),
                  money(e.net_monthly.net_monthly_value!),
                ];
              })}
            />
          </Card>
          <Card
            title="Sensitivity: net monthly value (breakeven precision)"
            action={
              <div className="flex items-center gap-2">
                <Select label="Config" value={config} onChange={setConfig} options={ORDER.map((c) => ({ value: c, label: CONFIG_LABEL[c]! }))} />
                <ProvenanceBadge label="ASSUMPTION" />
              </div>
            }
          >
            <DataTable
              caption="Sensitivity table"
              columns={["Standard misroute cost", ...ev.sensitivity_grid.review_minutes.map((r) => `${r} min review`)]}
              rows={ev.sensitivity_grid.misroute_cost_standard.map((cost) => [
                `$${cost}`,
                ...ev.sensitivity_grid.review_minutes.map((mins) => {
                  const row = ev.configs[config]?.economics.sensitivity.find((x) => x.misroute_cost_standard === cost && x.review_minutes === mins);
                  return row ? (
                    <span key={mins} className={row.net_monthly_value < 0 ? "text-danger" : undefined}>
                      {money(row.net_monthly_value)} ({row.breakeven_precision?.toFixed(3) ?? "—"})
                    </span>
                  ) : (
                    "—"
                  );
                }),
              ])}
            />
          </Card>
        </>
      ) : own ? (
        <Card title="Owner's business case" action={<ProvenanceBadge label="ASSUMPTION" />}>
          <DataTable
            caption="Business case"
            columns={["Field", "Value"]}
            rows={Object.entries(own).map(([k, v]) => [label(k), typeof v === "string" ? v : `${v.value?.toLocaleString() ?? "—"} ${v.unit ?? ""}`])}
          />
        </Card>
      ) : (
        <EmptyState illustration="onboarding" title="No business case yet" missing="The owner records monthly volume, a value hypothesis, and a cost estimate before the app can leave intake." />
      )}
    </div>
  );
}

function Experiments({ ev }: { ev: Evidence | undefined }) {
  const [config, setConfig] = useState("llm_low_cost_v1");
  const [filter, setFilter] = useState("");
  if (!ev?.available) return <EmptyState illustration="no-experiments" title="No experiments" missing="Only managed apps run experiments through the control plane, and this app has none recorded." />;
  const rows: [string, string][] = [
    ["macro_f1", "Macro F1"],
    ["accuracy", "Accuracy"],
    ["automation_coverage", "Automation coverage"],
    ["auto_precision", "Auto precision"],
    ["review_rate", "Review rate"],
    ["abstention_rate", "Abstention rate"],
    ["latency_p50_ms", "Latency p50"],
    ["latency_p95_ms", "Latency p95"],
    ["model_cost_per_1k_usd", "Model cost per 1,000 cases"],
  ];
  const intents = (ev.configs[config]?.per_intent ?? []).filter((i) => i.intent.includes(filter.toLowerCase()));
  return (
    <div className="flex flex-col gap-6">
      <Card title="Three configs on the same 1,540 frozen cases" action={<ProvenanceBadge label="MEASURED" />}>
        <div className="relative overflow-x-auto">
          <DataTable caption="Config comparison" columns={["Metric", ...ORDER.map((c) => CONFIG_LABEL[c]!)]} rows={rows.map(([k, l]) => [l, ...ORDER.map((c) => m(ev.configs[c]?.scorecard ?? {}, k))])} />
        </div>
        <p className="t-label mt-3 break-all text-muted">Sources: {ORDER.map((c) => ev.configs[c]?.source).join(", ")}</p>
      </Card>
      <Card title="Paired bootstrap against the classifier (1,000 resamples, 95% interval)" action={<ProvenanceBadge label="MEASURED" />}>
        <DataTable
          caption="Bootstrap intervals"
          columns={["Candidate", "Metric", "Delta", "95% interval", "Reading"]}
          rows={ev.bootstrap.map((b) => {
            const sig = b.ci_low !== null && b.ci_high !== null && (b.ci_low > 0 || b.ci_high < 0);
            return [
              CONFIG_LABEL[b.candidate],
              label(b.metric),
              b.delta === null ? "—" : `${b.delta > 0 ? "+" : ""}${b.delta.toFixed(3)}`,
              b.ci_low === null ? "—" : `[${b.ci_low.toFixed(3)}, ${b.ci_high!.toFixed(3)}]`,
              sig ? (b.delta! > 0 ? "Better than the classifier" : "Worse than the classifier") : "No clear difference",
            ];
          })}
        />
      </Card>
      <Card
        title="Per intent drill down"
        action={
          <div className="flex flex-wrap gap-2">
            <Input aria-label="Filter intents" placeholder="Filter intents" value={filter} onChange={(e) => setFilter(e.target.value)} />
            <Select label="Config" value={config} onChange={setConfig} options={ORDER.map((c) => ({ value: c, label: CONFIG_LABEL[c]! }))} />
          </div>
        }
      >
        <div className="max-h-[480px] overflow-auto">
          <DataTable
            caption="Per intent results"
            columns={["Intent", "Cases", "Recall", "Precision", "Auto routed"]}
            rows={intents.map((i) => [
              <span key="i" className={cx(i.sensitive && "t-card")}>
                {i.intent}
                {i.sensitive && <span className="t-label ml-2 text-warning">sensitive</span>}
              </span>,
              i.support,
              pct(i.recall),
              pct(i.precision),
              pct(i.auto_rate),
            ])}
          />
        </div>
      </Card>
    </div>
  );
}

function Policy({ ev }: { ev: Evidence | undefined }) {
  const [config, setConfig] = useState("llm_low_cost_v1");
  const c = ev?.configs[config];
  if (!ev?.available || !c) return <EmptyState illustration="no-experiments" title="No decision policy" missing="Decision policies belong to managed apps." />;
  return (
    <div className="flex flex-col gap-6">
      <Card title={`Frozen policy ${c.policy.policy_id}`} action={<Select label="Config" value={config} onChange={setConfig} options={ORDER.map((x) => ({ value: x, label: CONFIG_LABEL[x]! }))} />}>
        <DataTable caption="Thresholds" columns={["Threshold", "Value"]} rows={Object.entries(c.policy.thresholds).map(([k, v]) => [label(k), v])} />
        <p className="t-label mt-3 text-muted">
          Tuned on the development set and frozen <span title={timestamp(c.policy.created_at)}>{relative(c.policy.created_at)}</span>, before the frozen evaluation. LLM self-reported confidence is never used.
        </p>
      </Card>
      <Card title="Sensitive intents always route to review">
        <ul className="t-body flex flex-wrap gap-2">
          {c.policy.sensitive_intents.map((i) => (
            <li key={i} className="rounded-full border border-line-strong px-3 py-1">
              {i}
            </li>
          ))}
        </ul>
      </Card>
      <CohortEditor
        appId="support-triage"
        eligible={c.policy.eligible_cohort}
        sensitive={c.policy.sensitive_intents}
        recall={(cand, intent) => ev.configs[cand]?.scorecard[`sensitive_recall.${intent}`]?.value ?? null}
      />
      <Card title="Where sensitive cases went (confusion filtered to sensitive intents)" action={<ProvenanceBadge label="MEASURED" />}>
        <DataTable
          caption="Sensitive confusion"
          columns={["Reference intent", "Predicted labels", "Auto", "Review", "Abstain"]}
          rows={c.sensitive_confusion.map((x) => [
            x.intent,
            Object.entries(x.predicted)
              .map(([k, v]) => `${k} ${v}`)
              .join(", "),
            <span key="a" className={x.routes.auto ? "text-danger" : undefined}>
              {x.routes.auto}
            </span>,
            x.routes.review,
            x.routes.abstain,
          ])}
        />
      </Card>
    </div>
  );
}

function Audit({ d }: { d: AppDetailData }) {
  return (
    <Card title={`${d.events.length} events, oldest first`}>
      <ol className="flex flex-col gap-3 border-l border-line pl-4">
        {d.events.map((e) => (
          <li key={e.event_id}>
            <span className="t-card">{e.kind === "stage_change" ? `${label(e.from_stage ?? "")} → ${label(e.to_stage ?? "")}` : label(e.kind)}</span>
            <span className="t-label block text-muted">
              {e.actor} · <span title={timestamp(e.created_at)}>{relative(e.created_at)}</span> · {e.reason}
              <span className="break-all">{e.evidence_refs.length > 0 && ` · evidence: ${e.evidence_refs.join(", ")}`}</span>
            </span>
          </li>
        ))}
      </ol>
    </Card>
  );
}

export default function AppDetail() {
  const { appId = "" } = useParams();
  const f = useUrlFilters();
  const { me } = useSession();
  const detail = useQuery({ queryKey: ["app", appId], queryFn: () => api.get<AppDetailData>(`/apps/${appId}`) });
  const ev = useQuery({ queryKey: ["evidence", appId], queryFn: () => api.get<Evidence>(`/apps/${appId}/evidence`), enabled: !!detail.data && !detail.data.external });
  const d = detail.data;
  const tabs = d?.external ? ALL_TABS.filter((t) => ["business", "monitoring", "audit"].includes(t.id)) : ALL_TABS;
  const tab = (tabs.find((t) => t.id === f.get("tab"))?.id ?? "business") as TabId;
  if (detail.error) return <ModuleError error={detail.error} onRetry={() => void detail.refetch()} />;
  if (!d) return <Skeleton className="h-96" />;
  return (
    <>
      <HeaderBand page="applications" title={d.app.name} summary={`${d.card.business_unit} · ${label(d.card.platform)} · ${label(d.card.stage)} · owner ${d.card.owner ?? "none"}`}>
        <div className="flex flex-wrap items-center gap-3">
          <HealthPill health={d.card.health} rule={d.card.health_rule} />
          <MetricInline metric={d.card.monthly_spend_usd} title="Monthly spend" />
          <Link to={`/pipeline?stage=${d.card.stage}`} className="t-label text-accent hover:underline">
            Show on pipeline
          </Link>
        </div>
      </HeaderBand>
      <div role="tablist" aria-label="App detail" className="mb-6 flex gap-1 relative overflow-x-auto border-b border-line">
        {tabs.map((t) => (
          <button
            key={t.id}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls={`panel-${t.id}`}
            onClick={() => f.set({ tab: t.id === "business" ? null : t.id })}
            className={cx("m-hover min-h-11 border-b-2 px-4 t-card whitespace-nowrap", tab === t.id ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink")}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {ev.isLoading && !d.external && tab !== "audit" ? (
          <Skeleton className="h-64" />
        ) : tab === "business" ? (
          <BusinessCase d={d} ev={ev.data} />
        ) : tab === "experiments" ? (
          <Experiments ev={ev.data} />
        ) : tab === "policy" ? (
          <Policy ev={ev.data} />
        ) : tab === "shadow" ? (
          <ShadowTab appId={appId} />
        ) : tab === "release" ? (
          d.external ? <EmptyState illustration="no-experiments" title="No releases" missing="Release gates apply to managed apps." /> : <ReleaseTab appId={appId} />
        ) : tab === "monitoring" ? (
          d.external ? <EmptyState illustration="stale" title="No monitoring signals" missing="External platforms report usage through imports; daily model signals apply to managed apps." /> : <MonitoringTab appId={appId} />
        ) : (
          <Audit d={d} />
        )}
      </div>
      <span className="sr-only">{me?.email}</span>
    </>
  );
}
