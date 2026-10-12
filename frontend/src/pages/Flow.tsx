// Flow (console spec Section 9): how apps move through the lifecycle over a period.
import { useQuery } from "@tanstack/react-query";
import { lazy, Suspense, useEffect } from "react";
import { useNavigate } from "react-router";
import { ChartFrame, DataTable, HeaderBand, KpiCard, ProvenanceBadge, Skeleton, Card } from "../components/ui";
import { api, query, type Metric } from "../lib/api";
import { label, money, pct } from "../lib/format";
import { track, useUrlFilters } from "../lib/state";

const StageSankey = lazy(() => import("../charts/FlowCharts").then((m) => ({ default: m.StageSankey })));
const WeeklyInOut = lazy(() => import("../charts/FlowCharts").then((m) => ({ default: m.WeeklyInOut })));

interface Board {
  name: string;
  shipped: number;
  median_cycle_days: number | null;
  spend: number;
}
interface FlowData {
  range_days: number;
  header: Record<"apps_entered" | "apps_to_production" | "median_days_to_production" | "approval_rate", Metric>;
  approval_rate_detail: { published: number; rejected: number };
  sankey: { source: string; target: string; value: number }[];
  weekly: { week_start: string; in: number; out: number }[];
  weekly_prior: { week_start: string; in: number; out: number }[];
  stage_medians: { stage: string; median_days: number; stays: number }[];
  leaderboard: { owners: Board[]; business_units: Board[] };
  data_source: string;
  last_export_at: string | null;
}

function Leaderboard({ title, rows }: { title: string; rows: Board[] }) {
  return (
    <Card title={title}>
      <DataTable caption={title} columns={["Name", "Shipped", "Median cycle", "Spend"]} rows={rows.slice(0, 8).map((r) => [r.name, r.shipped, r.median_cycle_days === null ? "—" : `${r.median_cycle_days}d`, money(r.spend)])} />
    </Card>
  );
}

export default function Flow() {
  const f = useUrlFilters();
  const navigate = useNavigate();
  const data = useQuery({ queryKey: ["flow", f.platform, f.range], queryFn: () => api.get<FlowData>(`/flow${query({ platform: f.platform, range: f.range })}`) });
  useEffect(() => track("flow_filter_changed", "flow"), [f.platform, f.range]);
  const d = data.data;
  const toStage = (stage: string) => navigate(`/apps${query({ stage, platform: f.platform })}`);
  const busiest = d ? [...d.sankey].sort((a, b) => b.value - a.value)[0] : null;
  const slowest = d ? [...d.stage_medians].filter((s) => !["monitored", "retired", "paused"].includes(s.stage)).sort((a, b) => b.median_days - a.median_days)[0] : null;
  return (
    <>
      <HeaderBand page="flow" title="Flow" summary="How applications enter, advance, stall, and exit the lifecycle over the selected period.">
        <span className="t-label flex items-center gap-2 text-muted">
          Source: {d?.data_source ?? "…"} · Last export: {d?.last_export_at ?? "not yet exported"} <ProvenanceBadge label="SYNTHETIC" />
        </span>
      </HeaderBand>
      <div className="grid grid-cols-1 gap-6 min-[720px]:grid-cols-2 min-[1280px]:grid-cols-4">
        <KpiCard title="Apps entered" metric={d?.header.apps_entered} loading={data.isLoading} error={data.error} onRetry={() => void data.refetch()} hint={`last ${f.range} days`} />
        <KpiCard title="Reached production" metric={d?.header.apps_to_production} loading={data.isLoading} error={data.error} hint={`last ${f.range} days`} />
        <KpiCard title="Median days to production" metric={d?.header.median_days_to_production} loading={data.isLoading} error={data.error} />
        <div title={d ? `Approval rate = published / (published + rejected) in the last ${f.range} days. Population: ${d.approval_rate_detail.published} published, ${d.approval_rate_detail.rejected} rejected.` : ""}>
          <KpiCard title="Approval rate" metric={d?.header.approval_rate} loading={data.isLoading} error={data.error} hint={d ? `${d.approval_rate_detail.published} of ${d.approval_rate_detail.published + d.approval_rate_detail.rejected}` : undefined} />
        </div>
        <div className="min-[720px]:col-span-2 min-[1280px]:col-span-4">
          <ChartFrame
            title={busiest ? `Most movement: ${label(busiest.source)} to ${label(busiest.target)} (${busiest.value} moves)` : "Stage transitions"}
            hint="Moves between stages in the period · click a stage to list its apps"
            provenance={["FIXTURE"]}
            loading={data.isLoading}
            error={data.error}
            onRetry={() => void data.refetch()}
            empty={d && d.sankey.length === 0 ? { title: "No moves in this period", missing: "Widen the date range to see transitions." } : null}
            height={300}
            table={<DataTable caption="Stage transitions" columns={["From", "To", "Moves"]} rows={(d?.sankey ?? []).map((l) => [label(l.source), label(l.target), l.value])} />}
          >
            {d && (
              <Suspense fallback={<Skeleton className="h-[300px]" />}>
                <StageSankey links={d.sankey} onSelect={toStage} />
              </Suspense>
            )}
          </ChartFrame>
        </div>
        <div className="min-[720px]:col-span-2">
          <ChartFrame
            title={d ? `${d.weekly.reduce((s, w) => s + w.in, 0)} apps entered and ${d.weekly.reduce((s, w) => s + w.out, 0)} retired` : "Weekly in and out"}
            hint="Bars: this period · line: prior period entries · click a week to list apps"
            provenance={["FIXTURE"]}
            loading={data.isLoading}
            error={data.error}
            height={240}
            table={<DataTable caption="Weekly in and out" columns={["Week", "Entered", "Retired", "Entered prior"]} rows={(d?.weekly ?? []).map((w, i) => [w.week_start, w.in, w.out, d?.weekly_prior[i]?.in ?? "—"])} />}
          >
            {d && (
              <Suspense fallback={<Skeleton className="h-[240px]" />}>
                <WeeklyInOut weeks={d.weekly} prior={d.weekly_prior} onSelect={() => navigate(`/apps${query({ platform: f.platform, sort: "recent" })}`)} />
              </Suspense>
            )}
          </ChartFrame>
        </div>
        <div className="min-[720px]:col-span-2">
          <Card title={slowest ? `${label(slowest.stage)} is the slowest queue (${slowest.median_days} days median)` : "Median days in each stage"}>
            {d ? (
              <DataTable caption="Median days in each stage" columns={["Stage", "Median days", "Completed stays"]} rows={d.stage_medians.map((s) => [label(s.stage), s.median_days, s.stays])} />
            ) : (
              <Skeleton className="h-48" />
            )}
            <div className="mt-2 flex justify-end">
              <ProvenanceBadge label="FIXTURE" />
            </div>
          </Card>
        </div>
        {d && (
          <>
            <div className="min-[720px]:col-span-2">
              <Leaderboard title="Owners by apps shipped" rows={d.leaderboard.owners} />
            </div>
            <div className="min-[720px]:col-span-2">
              <Leaderboard title="Business units by apps shipped" rows={d.leaderboard.business_units} />
            </div>
          </>
        )}
      </div>
      <span className="sr-only">{d ? pct(d.header.approval_rate.value) : ""}</span>
    </>
  );
}
