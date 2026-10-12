// Shadow, Release, Monitoring, and the cohort editor (Sections 6.6 to 6.8).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, OctagonAlert } from "lucide-react";
import { lazy, Suspense, useMemo, useState } from "react";
import { useSession } from "../../components/Shell";
import { Button, Card, ChartFrame, DataTable, EmptyState, ProvenanceBadge, Select, Skeleton, StatusText, Textarea, useToast } from "../../components/ui";
import { api, ApiError } from "../../lib/api";
import { label, money, pct, relative, timestamp } from "../../lib/format";
import { useApplyAppEvent } from "../../lib/state";
import type { ShadowDay, SignalDay } from "../../charts/SignalCharts";

const AgreementChart = lazy(() => import("../../charts/SignalCharts").then((m) => ({ default: m.AgreementChart })));
const ValueChart = lazy(() => import("../../charts/SignalCharts").then((m) => ({ default: m.ValueChart })));
const SignalChart = lazy(() => import("../../charts/SignalCharts").then((m) => ({ default: m.SignalChart })));

interface Gate {
  gate: string;
  threshold: number;
  observed: number | null;
  passed: boolean;
  comparison: string;
}
interface GateSet {
  gates: Gate[];
  all_passed: boolean;
}
export interface ReleaseRecord {
  release_id: string;
  candidate_config_id: string;
  baseline_config_id: string;
  cohort: string[];
  cohort_excluded: string[];
  full_candidate: GateSet;
  cohort_candidate: GateSet;
  proposed_by: string;
  proposed_at: string;
  decision: string | null;
  rationale: string | null;
  decided_by: string | null;
  decided_at: string | null;
  shadow_ref: string | null;
}

const CANDIDATES: Record<string, string> = { llm_high_capability_v1: "Gemini 3.8 Flash", llm_low_cost_v1: "Gemini 3.1 Flash-Lite" };

function GateTable({ set, caption }: { set: GateSet; caption: string }) {
  return (
    <DataTable
      caption={caption}
      columns={["Gate", "Threshold", "Observed", "Result"]}
      rows={set.gates.map((g) => [
        label(g.gate.replace("sensitive_recall.", "sensitive recall: ")),
        `${g.comparison} ${g.gate === "latency_p95_ms" ? g.threshold.toLocaleString() : g.threshold.toFixed(3)}`,
        g.observed === null ? "—" : g.gate === "latency_p95_ms" ? g.observed.toLocaleString() : g.observed.toFixed(3),
        g.passed ? (
          <StatusText key="r" tone="healthy" icon={CheckCircle2}>
            Pass
          </StatusText>
        ) : (
          <StatusText key="r" tone="danger" icon={OctagonAlert}>
            Fail
          </StatusText>
        ),
      ])}
    />
  );
}

function DecisionForm({ appId, release }: { appId: string; release: ReleaseRecord }) {
  const toast = useToast();
  const qc = useQueryClient();
  const apply = useApplyAppEvent();
  const [decision, setDecision] = useState("withhold");
  const [rationale, setRationale] = useState("");
  const m = useMutation({
    mutationFn: () => api.post(`/apps/${appId}/releases/${release.release_id}/decide`, { decision, rationale }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["releases", appId] });
      apply({ app_id: appId });
      toast({ kind: "success", message: `Decision recorded: ${label(decision)}` });
    },
  });
  const blocked = (decision === "activate_full" && !release.full_candidate.all_passed) || (decision === "activate_cohort" && !release.cohort_candidate.all_passed);
  return (
    <form
      className="mt-4 flex flex-col gap-3 rounded-lg border border-line-strong p-4"
      onSubmit={(e) => {
        e.preventDefault();
        m.mutate();
      }}
    >
      <h4 className="t-card">Record the decision</h4>
      <Select
        label="Decision"
        value={decision}
        onChange={setDecision}
        options={[
          { value: "withhold", label: "Withhold" },
          { value: "reject", label: "Reject" },
          { value: "activate_cohort", label: `Activate cohort${release.cohort_candidate.all_passed ? "" : " (blocked: cohort gates fail)"}` },
          { value: "activate_full", label: `Activate full${release.full_candidate.all_passed ? "" : " (blocked: gates fail)"}` },
        ]}
      />
      <label className="t-label flex flex-col gap-1 text-muted">
        Rationale (at least 20 characters, cites the scorecard)
        <Textarea rows={3} value={rationale} onChange={(e) => setRationale(e.target.value)} />
      </label>
      {blocked && <p className="t-label text-danger">This decision is blocked because its gates fail. The server enforces the same rule.</p>}
      {m.error && <p className="t-label text-danger">{m.error instanceof ApiError ? m.error.message : "Failed"}</p>}
      <div>
        <Button type="submit" variant="primary" loading={m.isPending} disabled={blocked || rationale.trim().length < 20}>
          Record decision
        </Button>
      </div>
    </form>
  );
}

export function ReleaseTab({ appId }: { appId: string }) {
  const { me } = useSession();
  const releases = useQuery({ queryKey: ["releases", appId], queryFn: () => api.get<ReleaseRecord[]>(`/apps/${appId}/releases`) });
  if (releases.isLoading) return <Skeleton className="h-96" />;
  if (!releases.data?.length) return <EmptyState illustration="no-experiments" title="No release proposals" missing="An app owner proposes a release from the Decision Policy tab once a candidate has a frozen scorecard." />;
  return (
    <div className="flex flex-col gap-6">
      {releases.data.map((r) => {
        const full = r.full_candidate.gates.filter((g) => g.passed).length;
        const cohort = r.cohort_candidate.gates.filter((g) => g.passed).length;
        return (
          <Card
            key={r.release_id}
            title={`${CANDIDATES[r.candidate_config_id] ?? r.candidate_config_id}: ${r.decision ? label(r.decision) : "awaiting decision"}`}
            action={<ProvenanceBadge label="MEASURED" />}
          >
            <p className="t-body text-muted">
              Proposed by {r.proposed_by} <span title={timestamp(r.proposed_at)}>{relative(r.proposed_at)}</span>. Full candidate passes {full} of {r.full_candidate.gates.length} gates; the {r.cohort.length}-intent cohort passes {cohort} of {r.cohort_candidate.gates.length}.
              {r.cohort_excluded.length > 0 && ` The cohort excludes ${r.cohort_excluded.join(", ")}.`}
            </p>
            <div className="mt-4 grid gap-6 min-[1280px]:grid-cols-2">
              <div>
                <h4 className="t-label mb-2 text-muted">Full candidate</h4>
                <GateTable set={r.full_candidate} caption="Full candidate gates" />
              </div>
              <div>
                <h4 className="t-label mb-2 text-muted">Proposed cohort (candidate inside, classifier outside)</h4>
                <GateTable set={r.cohort_candidate} caption="Cohort gates" />
              </div>
            </div>
            {r.decision ? (
              <div className="mt-4 rounded-lg border border-line p-4">
                <span className="t-card">
                  {label(r.decision)} by {r.decided_by} <span title={timestamp(r.decided_at)}>{relative(r.decided_at)}</span>
                </span>
                <p className="t-body mt-1 text-muted">{r.rationale}</p>
              </div>
            ) : me?.role === "governance_admin" ? (
              <DecisionForm appId={appId} release={r} />
            ) : (
              <p className="t-label mt-4 text-muted">A governance admin records the decision.</p>
            )}
          </Card>
        );
      })}
    </div>
  );
}

interface ShadowData {
  available: boolean;
  run_id: string;
  candidate_config_id: string;
  cohort: string[];
  days: (ShadowDay & { routes: Record<string, Record<string, number>> })[];
  totals: { cases: number; label_agreement: number; route_agreement: number; candidate_cost_usd: number; net_value_usd: Record<string, number>; accuracy: Record<string, number>; unknown_outcomes: number };
}

export function ShadowTab({ appId }: { appId: string }) {
  const q = useQuery({ queryKey: ["shadow", appId], queryFn: () => api.get<ShadowData>(`/apps/${appId}/shadow`) });
  const d = q.data;
  if (q.isLoading) return <Skeleton className="h-96" />;
  if (!d?.available) return <EmptyState illustration="no-shadow" title="No shadow runs yet" missing="cp shadow replays 14 simulated days with the approved config deciding and the candidate shadowing." />;
  const t = d.totals;
  const delta = t.net_value_usd.cohort! - t.net_value_usd.approved!;
  return (
    <div className="flex flex-col gap-6">
      <Card title={`${CANDIDATES[d.candidate_config_id]} shadowed classifier_v1 on ${t.cases.toLocaleString()} cases`} action={<ProvenanceBadge label="SIMULATED" />}>
        <dl className="grid grid-cols-2 gap-4 min-[1024px]:grid-cols-5">
          {[
            ["Label agreement", pct(t.label_agreement), "SIMULATED"],
            ["Route agreement", pct(t.route_agreement), "SIMULATED"],
            ["Candidate model cost", money(t.candidate_cost_usd), "MEASURED"],
            ["Accuracy: classifier / candidate", `${pct(t.accuracy.approved!)} / ${pct(t.accuracy.candidate!)}`, "SIMULATED"],
            ["Cohort net value vs classifier", `${delta >= 0 ? "+" : "−"}${money(Math.abs(delta))} over 14 days`, "ASSUMPTION"],
          ].map(([k, v, p]) => (
            <div key={k}>
              <dt className="t-label text-muted">{k}</dt>
              <dd className="t-card mt-1 flex flex-wrap items-center gap-2">
                {v} <ProvenanceBadge label={p as "SIMULATED"} />
              </dd>
            </div>
          ))}
        </dl>
        <p className="t-label mt-3 break-all text-muted">Run {d.run_id}. {t.unknown_outcomes} unknown outcomes held, never re-called.</p>
      </Card>
      <div className="grid gap-6 min-[1280px]:grid-cols-2">
        <ChartFrame
          title={`Models agree on ${pct(t.label_agreement)} of labels; candidate spend ${money(t.candidate_cost_usd)}`}
          hint="Daily label and route agreement, and candidate model cost"
          provenance={["SIMULATED", "MEASURED"]}
          height={240}
          table={<DataTable caption="Daily agreement" columns={["Day", "Cases", "Label agreement", "Route agreement", "Cost"]} rows={d.days.map((x) => [x.day, x.cases, pct(x.label_agreement), pct(x.route_agreement), money(x.candidate_cost_usd)])} />}
        >
          <Suspense fallback={<Skeleton className="h-[240px]" />}>
            <AgreementChart days={d.days} />
          </Suspense>
        </ChartFrame>
        <ChartFrame
          title={delta >= 0 ? `The cohort would add ${money(delta)} over 14 days` : `The cohort would cost ${money(-delta)} over 14 days`}
          hint="Daily net value: classifier alone, proposed cohort, full candidate"
          provenance={["ASSUMPTION"]}
          height={240}
          table={<DataTable caption="Daily net value" columns={["Day", "Classifier", "Cohort", "Full candidate"]} rows={d.days.map((x) => [x.day, money(x.net_value_usd.approved), money(x.net_value_usd.cohort), money(x.net_value_usd.candidate)])} />}
        >
          <Suspense fallback={<Skeleton className="h-[240px]" />}>
            <ValueChart days={d.days} />
          </Suspense>
        </ChartFrame>
      </div>
      <Card title="Route comparison by day" action={<ProvenanceBadge label="SIMULATED" />}>
        <DataTable
          caption="Routes by day"
          columns={["Day", "Classifier auto / review", "Candidate auto / review / abstain", "Cohort auto / review / abstain"]}
          rows={d.days.map((x) => [
            x.day,
            `${x.routes.approved!.auto} / ${x.routes.approved!.review}`,
            `${x.routes.candidate!.auto} / ${x.routes.candidate!.review} / ${x.routes.candidate!.abstain}`,
            `${x.routes.cohort!.auto} / ${x.routes.cohort!.review} / ${x.routes.cohort!.abstain}`,
          ])}
        />
      </Card>
    </div>
  );
}

interface MonitoringData {
  available: boolean;
  drill: { drill_days: number[]; days: (SignalDay & { breaches: { signal: string }[] })[]; timeline: { day: number; event: string; actor: string; detail: string }[]; incident: { incident_id: string; opened_day: number; detection_delay_days: number; status: string } | null; detected: boolean };
  alert_policy: { policy_id: string; frozen_at: string; thresholds: Record<string, { value: number; direction: string; baseline_mean: number }> };
}

export function MonitoringTab({ appId }: { appId: string }) {
  const q = useQuery({ queryKey: ["monitoring", appId], queryFn: () => api.get<MonitoringData>(`/apps/${appId}/monitoring`) });
  const d = q.data;
  if (q.isLoading) return <Skeleton className="h-96" />;
  if (!d?.available) return <EmptyState illustration="stale" title="No monitoring signals yet" missing="Monitoring runs over the shadow days once an alert policy is frozen (cp monitor freeze, then cp drill)." />;
  const th = d.alert_policy.thresholds;
  const inc = d.drill.incident;
  const charts: [keyof typeof th, "review_rate" | "cost_per_correct_usd" | "sampled_accuracy", string, "pct" | "usd"][] = [
    ["review_rate", "review_rate", "Review rate", "pct"],
    ["cost_per_correct_usd", "cost_per_correct_usd", "Cost per correct", "usd"],
    ["sampled_accuracy", "sampled_accuracy", "Sampled accuracy", "pct"],
  ];
  return (
    <div className="flex flex-col gap-6">
      <Card title={inc ? `Drift detected on day ${inc.opened_day}, ${inc.detection_delay_days} day(s) after it began` : "The drill's drift was not detected"} action={<ProvenanceBadge label="FIXTURE" />}>
        <p className="t-body text-muted">
          Production config: classifier_v1. Thresholds come from simulated days 1 to 7 and were frozen <span title={timestamp(d.alert_policy.frozen_at)}>{relative(d.alert_policy.frozen_at)}</span>, before the drill. Drift cases (FIXTURE) were injected on days {d.drill.drill_days.join(", ")} (shaded).
        </p>
        <ol className="t-body mt-3 list-decimal pl-5">
          {d.drill.timeline.map((e, i) => (
            <li key={i}>
              Day {e.day}: {label(e.event)} ({e.actor}). {e.detail}
            </li>
          ))}
        </ol>
      </Card>
      <div className="grid gap-6 min-[1280px]:grid-cols-3">
        {charts.map(([key, field, name, unit]) => (
          <ChartFrame
            key={key}
            title={`${name}: alert ${th[key]!.direction} ${unit === "pct" ? pct(th[key]!.value) : money(th[key]!.value)}`}
            hint="Daily signal with its frozen alert line"
            provenance={["SIMULATED", "FIXTURE"]}
            height={200}
            table={<DataTable caption={name} columns={["Day", name, "Authority", "Breach"]} rows={d.drill.days.map((x) => [x.day, x[field] === null ? "paused" : unit === "pct" ? pct(x[field]) : money(x[field]), x.authority, x.breaches.some((b) => b.signal === key) ? "yes" : "—"])} />}
          >
            <Suspense fallback={<Skeleton className="h-[200px]" />}>
              <SignalChart days={d.drill.days} field={field} threshold={th[key]!.value} label={name} unit={unit} drillDays={d.drill.drill_days} incidentDay={inc?.opened_day ?? null} />
            </Suspense>
          </ChartFrame>
        ))}
      </div>
    </div>
  );
}

export function CohortEditor({ appId, eligible, sensitive, recall }: { appId: string; eligible: string[]; sensitive: string[]; recall: (candidate: string, intent: string) => number | null }) {
  const { readOnly, me } = useSession();
  const toast = useToast();
  const qc = useQueryClient();
  const [candidate, setCandidate] = useState("llm_high_capability_v1");
  const initial = useMemo(() => new Set(eligible.filter((i) => !sensitive.includes(i) || (recall(candidate, i) ?? 0) >= 0.95)), [eligible, sensitive, recall, candidate]);
  const [cohort, setCohort] = useState<Set<string> | null>(null);
  const current = cohort ?? initial;
  const preview = useMutation({ mutationFn: () => api.post<GateSet>(`/apps/${appId}/releases/preview`, { candidate_config_id: candidate, cohort: [...current] }) });
  const propose = useMutation({
    mutationFn: () => api.post<ReleaseRecord>(`/apps/${appId}/releases`, { candidate_config_id: candidate, cohort: [...current] }),
    onSuccess: (r) => {
      void qc.invalidateQueries({ queryKey: ["releases", appId] });
      toast({ kind: "success", message: `Proposed ${r.release_id}` });
    },
    onError: (e: Error) => toast({ kind: "error", message: e.message }),
  });
  const canPropose = !readOnly && me?.role === "app_owner";
  return (
    <Card
      title={`Cohort editor: ${current.size} of ${eligible.length} intents`}
      action={<Select label="Candidate" value={candidate} onChange={(v) => { setCandidate(v); setCohort(null); preview.reset(); }} options={Object.entries(CANDIDATES).map(([value, l]) => ({ value, label: l }))} />}
    >
      <p className="t-body text-muted">Inside the cohort the candidate decides; outside it, classifier_v1 decides. The default excludes sensitive intents whose candidate recall is below 0.95. Gate previews use the frozen results and make no model calls.</p>
      <h4 className="t-label mt-4 mb-2 text-muted">Sensitive intents</h4>
      <ul className="grid grid-cols-1 gap-2 min-[720px]:grid-cols-2">
        {sensitive.map((i) => {
          const r = recall(candidate, i);
          return (
            <li key={i} className="t-body flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line px-3 py-2">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  className="size-5"
                  checked={current.has(i)}
                  disabled={readOnly}
                  onChange={(e) => {
                    const next = new Set(current);
                    if (e.target.checked) next.add(i);
                    else next.delete(i);
                    setCohort(next);
                    preview.reset();
                  }}
                />
                {i}
              </label>
              <span className={r !== null && r < 0.95 ? "t-label text-danger" : "t-label text-healthy"}>recall {pct(r)}</span>
            </li>
          );
        })}
      </ul>
      <p className="t-label mt-2 text-muted">The other {eligible.length - sensitive.length} intents are included.</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button variant="primary" loading={preview.isPending} onClick={() => preview.mutate()}>
          Preview gates
        </Button>
        {canPropose && (
          <Button loading={propose.isPending} onClick={() => propose.mutate()}>
            Propose release with this cohort
          </Button>
        )}
      </div>
      {preview.data && (
        <div className="mt-4">
          <p className="t-card mb-2">
            {preview.data.gates.filter((g) => g.passed).length} of {preview.data.gates.length} gates pass {preview.data.all_passed ? "— this cohort could be activated" : "— activation would be blocked"}
          </p>
          <GateTable set={preview.data} caption="Cohort gate preview" />
        </div>
      )}
    </Card>
  );
}
