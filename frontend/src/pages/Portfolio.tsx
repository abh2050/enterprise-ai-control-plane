// Portfolio (console spec Section 9).
import { useQuery } from "@tanstack/react-query";
import { CalendarClock, Download, FileText, LayoutGrid, Rows3, ShieldAlert } from "lucide-react";
import { lazy, Suspense, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { AppDrawer } from "../components/AppDrawer";
import { AssistDrawer } from "../components/AssistDrawer";
import { useSession } from "../components/Shell";
import {
  Button,
  Card,
  ChartFrame,
  DataTable,
  Drawer,
  EmptyState,
  HeaderBand,
  HealthPill,
  Input,
  KpiCard,
  MetricInline,
  ModuleError,
  ProvenanceBadge,
  Select,
  Skeleton,
  Sparkline,
} from "../components/ui";
import { api, query, SNAPSHOT, STAGES, type AppCard, type Metric, type PortfolioData } from "../lib/api";
import { compact, label, money, relative, timestamp } from "../lib/format";
import { now as clockNow } from "../lib/clock";
import { track, useUrlFilters } from "../lib/state";

const Matrix = lazy(() => import("../charts/PortfolioCharts").then((m) => ({ default: m.InvestmentMatrix })));
const PlatformBars = lazy(() => import("../charts/PortfolioCharts").then((m) => ({ default: m.PlatformBars })));

function StripItem({ title, metric, to }: { title: string; metric: Metric; to: string }) {
  return (
    <Link to={to} onClick={() => track("metric_drilldown_opened", "portfolio")} className="m-hover flex min-h-11 items-center gap-2 rounded-lg px-3 hover:bg-raised">
      <span className="t-label text-muted">{title}</span>
      <MetricInline metric={metric} title={title} />
    </Link>
  );
}

function SpendDrawer({ open, onClose, platform }: { open: boolean; onClose: () => void; platform: string }) {
  const q = useQuery({
    queryKey: ["spend", platform],
    queryFn: () => api.get<{ app_id: string; name: string; platform: string; spend: Metric }[]>(`/portfolio/spend${query({ platform })}`),
    enabled: open,
  });
  return (
    <Drawer open={open} onClose={onClose} title="Monthly spend by app" width={420}>
      {q.isLoading ? (
        <Skeleton className="h-64" />
      ) : q.error ? (
        <ModuleError error={q.error} onRetry={() => void q.refetch()} />
      ) : (
        <DataTable
          caption="Monthly spend by app"
          columns={["App", "Platform", "Spend"]}
          rows={(q.data ?? []).map((r) => [r.name, label(r.platform), <MetricInline key={r.app_id} metric={r.spend} />])}
        />
      )}
    </Drawer>
  );
}

function RankedList({ points, onOpen }: { points: PortfolioData["matrix"]["points"]; onOpen: (id: string) => void }) {
  const ranked = [...points].sort((a, b) => (b.value ?? 0) - b.cost - ((a.value ?? 0) - a.cost));
  return (
    <ol className="flex flex-col gap-2">
      {ranked.map((p, i) => (
        <li key={p.app_id}>
          <button type="button" onClick={() => onOpen(p.app_id)} className="m-hover flex min-h-11 w-full items-center justify-between rounded-lg border border-line px-3 text-left hover:bg-raised">
            <span className="t-body">
              {i + 1}. {p.name} <span className="t-label text-muted">({p.quadrant})</span>
            </span>
            <span className="t-label text-muted">
              {money(p.value)} value · {money(p.cost)} cost
            </span>
          </button>
        </li>
      ))}
    </ol>
  );
}

function useNarrow(px = 720) {
  const [narrow, setNarrow] = useState(() => window.innerWidth < px);
  useEffect(() => {
    const on = () => setNarrow(window.innerWidth < px);
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, [px]);
  return narrow;
}

function CatalogCard({ c, onOpen }: { c: AppCard; onOpen: () => void }) {
  return (
    <button type="button" onClick={onOpen} className="m-hover flex flex-col gap-3 rounded-xl border border-line bg-surface p-5 text-left hover:border-accent">
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className="t-card line-clamp-2">{c.name}</span>
          <span className="t-label block text-muted">
            {c.owner ?? "No owner"} · {c.business_unit}
          </span>
        </div>
        <HealthPill health={c.health} rule={c.health_rule} />
      </div>
      <div className="t-label flex flex-wrap gap-x-3 gap-y-1 text-muted">
        <span>{label(c.platform)}</span>
        <span>{label(c.stage)}</span>
        <span>{label(c.risk_tier)} risk</span>
        <span title={`${c.days_in_stage.value} days (${c.days_in_stage.provenance})`}>{c.days_in_stage.value}d in stage</span>
      </div>
      <div className="flex items-end justify-between gap-2">
        <MetricInline metric={c.monthly_spend_usd} title="Monthly spend" />
        <Sparkline values={c.usage_series} label={`${c.name} usage`} />
      </div>
      <span className="t-label truncate text-muted" title={c.last_decision ?? ""}>
        Last decision: {c.last_decision ?? "none"}
      </span>
    </button>
  );
}

function Catalog({ onOpen }: { onOpen: (id: string) => void }) {
  const f = useUrlFilters();
  const { me } = useSession();
  const narrow = useNarrow();
  const view = narrow ? "cards" : f.get("view", "cards");
  const params = {
    platform: f.platform,
    q: f.get("q"),
    stage: f.get("stage"),
    risk: f.get("risk"),
    owner: f.get("owner"),
    business_unit: f.get("bu"),
    health: f.get("health"),
    spend_min: f.get("spend_min"),
    spend_max: f.get("spend_max"),
    stalled: f.get("stalled"),
    sort: f.get("sort", "spend"),
  };
  const cards = useQuery({ queryKey: ["apps", "catalog", params], queryFn: () => api.get<AppCard[]>(`/apps${query(params)}`) });
  const all = useQuery({ queryKey: ["apps", "all", f.platform], queryFn: () => api.get<AppCard[]>(`/apps${query({ platform: f.platform })}`) });
  const owners = [...new Set((all.data ?? []).map((c) => c.owner).filter(Boolean))] as string[];
  const units = [...new Set((all.data ?? []).map((c) => c.business_unit))];
  const csvHref = `/export/catalog.csv${query({ platform: f.platform, stage: params.stage, q: params.q, health: params.health })}`;
  return (
    <section aria-labelledby="catalog-h" className="mt-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 id="catalog-h" className="t-card">
          Portfolio catalog
          {cards.data && <span className="t-label ml-2 text-muted">{cards.data.length} apps</span>}
        </h2>
        <div className="no-print flex flex-wrap gap-2">
          {!narrow && (
            <div role="group" aria-label="Catalog view" className="flex rounded-lg border border-line-strong">
              <Button variant={view === "cards" ? "primary" : "ghost"} icon={LayoutGrid} aria-pressed={view === "cards"} onClick={() => f.set({ view: null })} className="min-h-9 rounded-r-none">
                Cards
              </Button>
              <Button variant={view === "table" ? "primary" : "ghost"} icon={Rows3} aria-pressed={view === "table"} onClick={() => f.set({ view: "table" })} className="min-h-9 rounded-l-none">
                Table
              </Button>
            </div>
          )}
          {me?.role === "governance_admin" && !SNAPSHOT && (
            <>
              <Button
                icon={Download}
                onClick={async () => {
                  const csv = await api.text(csvHref);
                  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
                  const a = Object.assign(document.createElement("a"), { href: url, download: "catalog.csv" });
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                Export CSV
              </Button>
              <Button icon={FileText} onClick={() => window.print()}>
                Export PDF
              </Button>
            </>
          )}
        </div>
      </div>
      <div className="no-print mb-4 grid grid-cols-2 gap-3 min-[720px]:grid-cols-4 min-[1280px]:grid-cols-8">
        <Input aria-label="Search catalog" placeholder="Search name, owner, problem" defaultValue={params.q} onChange={(e) => f.set({ q: e.target.value || null })} className="col-span-2" />
        <Select label="Stage" value={params.stage} onChange={(v) => f.set({ stage: v || null })} options={[{ value: "", label: "All stages" }, ...STAGES.map((s) => ({ value: s, label: label(s) }))]} />
        <Select label="Risk tier" value={params.risk} onChange={(v) => f.set({ risk: v || null })} options={[{ value: "", label: "All risk" }, ...["low", "medium", "high"].map((s) => ({ value: s, label: label(s) }))]} />
        <Select label="Owner" value={params.owner} onChange={(v) => f.set({ owner: v || null })} options={[{ value: "", label: "All owners" }, ...owners.map((o) => ({ value: o, label: o }))]} />
        <Select label="Business unit" value={params.business_unit} onChange={(v) => f.set({ bu: v || null })} options={[{ value: "", label: "All units" }, ...units.map((u) => ({ value: u, label: u }))]} />
        <Select label="Health" value={params.health} onChange={(v) => f.set({ health: v || null })} options={[{ value: "", label: "All health" }, ...["healthy", "warning", "danger"].map((s) => ({ value: s, label: label(s) }))]} />
        <Select
          label="Sort"
          value={params.sort}
          onChange={(v) => f.set({ sort: v })}
          options={[
            { value: "spend", label: "Spend" },
            { value: "value", label: "Value" },
            { value: "days", label: "Days in stage" },
            { value: "recent", label: "Last activity" },
          ]}
        />
        <Input aria-label="Minimum monthly spend (USD)" placeholder="Min spend" inputMode="numeric" defaultValue={params.spend_min} onChange={(e) => f.set({ spend_min: e.target.value || null })} />
        <Input aria-label="Maximum monthly spend (USD)" placeholder="Max spend" inputMode="numeric" defaultValue={params.spend_max} onChange={(e) => f.set({ spend_max: e.target.value || null })} />
        {params.stalled && (
          <Button variant="ghost" onClick={() => f.set({ stalled: null })}>
            Clear stalled filter
          </Button>
        )}
      </div>
      {cards.isLoading ? (
        <div className="grid grid-cols-1 gap-4 min-[720px]:grid-cols-2 min-[1280px]:grid-cols-4">
          {Array.from({ length: 8 }, (_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      ) : cards.error ? (
        <ModuleError error={cards.error} onRetry={() => void cards.refetch()} />
      ) : cards.data?.length === 0 ? (
        <EmptyState illustration="no-results" title="No apps match these filters" missing="Every app is filtered out." action={<Button onClick={() => f.set({ q: null, stage: null, risk: null, owner: null, bu: null, health: null, spend_min: null, spend_max: null, stalled: null })}>Clear filters</Button>} />
      ) : view === "table" ? (
        <div className="relative overflow-x-auto rounded-xl border border-line bg-surface p-4">
          <DataTable
            caption="Portfolio catalog"
            columns={["App", "Owner", "Unit", "Platform", "Stage", "Risk", "Days", "Spend", "Health", "Last decision"]}
            rows={(cards.data ?? []).map((c) => [
              <button key="n" type="button" className="t-card text-left hover:text-accent" onClick={() => onOpen(c.app_id)}>
                {c.name}
              </button>,
              c.owner ?? "No owner",
              c.business_unit,
              label(c.platform),
              label(c.stage),
              label(c.risk_tier),
              c.days_in_stage.value,
              <MetricInline key="s" metric={c.monthly_spend_usd} />,
              <HealthPill key="h" health={c.health} rule={c.health_rule} />,
              c.last_decision ?? "—",
            ])}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 min-[720px]:grid-cols-2 min-[1280px]:grid-cols-4">
          {(cards.data ?? []).map((c) => (
            <CatalogCard key={c.app_id} c={c} onOpen={() => onOpen(c.app_id)} />
          ))}
        </div>
      )}
    </section>
  );
}

export default function Portfolio() {
  const f = useUrlFilters();
  const navigate = useNavigate();
  const narrow = useNarrow();
  const data = useQuery({
    queryKey: ["portfolio", f.platform, f.range],
    queryFn: () => api.get<PortfolioData>(`/portfolio${query({ platform: f.platform, range: f.range })}`),
    refetchInterval: SNAPSHOT ? false : 60_000,
  });
  useEffect(() => track("portfolio_viewed", "portfolio"), []);
  const p = data.data;
  const openApp = (id: string) => f.set({ app: id });
  const scope = `${f.platform ? label(f.platform) : "All platforms"} · last ${f.range} days`;
  return (
    <>
      <HeaderBand
        page="portfolio"
        variant={p?.incident_open ? "incident" : "default"}
        title="Portfolio"
        summary={p?.incident_open ? "An incident is open. Review the attention queue before approving new work." : "Every AI application in the organization, what it costs, and where a decision is needed."}
      >
        <span className="t-label text-muted">{scope}</span>
      </HeaderBand>

      <div className="grid grid-cols-1 gap-6 min-[720px]:grid-cols-2 min-[1280px]:grid-cols-12">
        <div className="min-[1280px]:col-span-4">
          <KpiCard title="Apps in production" metric={p?.kpis.apps_in_production} loading={data.isLoading} error={data.error} onRetry={() => void data.refetch()} onClick={() => navigate("/pipeline?stage=monitored")} hint="Open on the pipeline" updatedAt={p?.generated_at} />
        </div>
        <div className="min-[1280px]:col-span-4">
          <KpiCard
            title="Monthly model spend (settled attempts)"
            metric={p?.kpis.monthly_model_spend_usd}
            loading={data.isLoading}
            error={data.error}
            onRetry={() => void data.refetch()}
            onClick={() => f.set({ spend: "1" })}
            hint={p ? `+ ${money(p.kpis.imported_spend_usd.value)} imported` : undefined}
            updatedAt={p?.generated_at}
          />
        </div>
        <div className="min-[720px]:col-span-2 min-[1280px]:col-span-4">
          <KpiCard
            title="Governance Assist: value at risk"
            metric={p?.kpis.value_at_risk_usd}
            loading={data.isLoading}
            error={data.error}
            onRetry={() => void data.refetch()}
            onClick={() => f.set({ assist: "1" })}
            hint={p ? `${p.assist.flagged_count} apps · ${p.assist.top_reason ?? "no reason"} · Review apps` : undefined}
            updatedAt={p?.generated_at}
          />
        </div>

        <div className="flex min-h-12 flex-wrap items-center gap-1 rounded-xl border border-line bg-surface px-2 min-[720px]:col-span-2 min-[1280px]:col-span-12">
          {p ? (
            <>
              <StripItem title="Total apps" metric={p.secondary.total_apps} to={`/apps${query({ platform: f.platform })}`} />
              <StripItem title="Stalled (1.5x stage median)" metric={p.secondary.stalled_apps} to={`/portfolio${query({ platform: f.platform, stalled: "1" })}#catalog-h`} />
              <StripItem title="Est. monthly value" metric={p.secondary.estimated_monthly_value_usd} to={`/portfolio${query({ platform: f.platform, sort: "value" })}#catalog-h`} />
              <StripItem title="Open incidents" metric={p.secondary.open_incidents} to="/incidents" />
              <StripItem title="Approvals waiting" metric={p.secondary.approvals_waiting} to="/reviews" />
            </>
          ) : (
            <Skeleton className="h-6 w-full" />
          )}
        </div>

        <div className="min-[720px]:col-span-2 min-[1280px]:col-span-8">
          <ChartFrame
            title={
              p
                ? `${p.matrix.points.filter((x) => x.quadrant === "Scale").length} apps are worth scaling; ${p.matrix.points.filter((x) => x.quadrant === "Retire").length} cost more than they return`
                : "Investment matrix"
            }
            hint={`Monthly cost vs estimated value · bubble size is volume · color and shape are risk tier · ${scope} · click a bubble to open it`}
            provenance={["FIXTURE", "ASSUMPTION"]}
            loading={data.isLoading}
            error={data.error}
            onRetry={() => void data.refetch()}
            height={232}
            table={
              <DataTable
                caption="Investment matrix"
                columns={["App", "Quadrant", "Cost", "Value", "Risk"]}
                rows={(p?.matrix.points ?? []).map((x) => [x.name, x.quadrant ?? "", money(x.cost), money(x.value), label(x.risk_tier)])}
              />
            }
          >
            {p &&
              (narrow ? (
                <RankedList points={p.matrix.points} onOpen={openApp} />
              ) : (
                <div className="flex gap-4">
                  <div className="relative min-w-0 flex-1">
                    <Suspense fallback={<Skeleton className="h-[232px]" />}>
                      <Matrix data={p.matrix} onOpen={openApp} />
                    </Suspense>
                    <div className="t-label pointer-events-none absolute inset-0 grid grid-cols-2 grid-rows-2 pt-0.5 pr-4 pb-0.5 pl-24 text-muted opacity-70" aria-hidden>
                      <span>Scale</span>
                      <span className="text-right">Fix</span>
                      <span className="self-end">Watch</span>
                      <span className="self-end text-right">Retire</span>
                    </div>
                  </div>
                  <aside className="w-40 shrink-0 rounded-lg border border-dashed border-line-strong p-3" aria-label="Needs business case">
                    <h3 className="t-label mb-2">Needs business case</h3>
                    <ul className="flex flex-col gap-1">
                      {p.matrix.needs_business_case.map((x) => (
                        <li key={x.app_id}>
                          <button type="button" className="t-label text-left font-normal text-muted underline-offset-2 hover:underline" onClick={() => openApp(x.app_id)}>
                            {x.name}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </aside>
                </div>
              ))}
          </ChartFrame>
        </div>

        <div className="min-[720px]:col-span-2 min-[1280px]:col-span-4">
          <Card title={<h2 className="t-card flex items-center gap-2"><ShieldAlert size={16} strokeWidth={1.75} aria-hidden /> Attention queue</h2>} className="h-full" updatedAt={p?.generated_at}>
            {data.isLoading ? (
              <Skeleton className="h-56" />
            ) : data.error ? (
              <ModuleError error={data.error} onRetry={() => void data.refetch()} />
            ) : p?.attention.length === 0 ? (
              <EmptyState illustration="no-results" title="Nothing needs action" missing="No app has an Assist reason right now." />
            ) : (
              <ol className="flex max-h-[232px] flex-col gap-2 overflow-y-auto pr-1">
                {p?.attention.map((r, i) => (
                  <li key={r.app_id}>
                    <button type="button" onClick={() => openApp(r.app_id)} className="m-hover w-full rounded-lg px-2 py-1 text-left hover:bg-raised">
                      <span className="t-card flex justify-between gap-2">
                        <span>
                          {i + 1}. {r.name}
                        </span>
                        <span className={r.score >= (p?.assist.threshold ?? 0.65) ? "text-danger" : "text-warning"}>{Math.round(r.score * 100)}</span>
                      </span>
                      <span className="t-label block font-normal text-muted">
                        {r.reason} — {r.action}
                      </span>
                    </button>
                  </li>
                ))}
              </ol>
            )}
          </Card>
        </div>

        <div className="min-[720px]:col-span-2 min-[1280px]:col-span-8">
          <ChartFrame
            title={p ? `${label([...p.platforms].sort((a, b) => b.spend - a.spend)[0]?.platform ?? "")} carries the most spend` : "Platform breakdown"}
            hint="App count and monthly spend by platform"
            provenance={["FIXTURE", "MEASURED"]}
            loading={data.isLoading}
            error={data.error}
            onRetry={() => void data.refetch()}
            height={150}
            table={<DataTable caption="Platform breakdown" columns={["Platform", "Apps", "Spend"]} rows={(p?.platforms ?? []).map((x) => [label(x.platform), x.apps, money(x.spend)])} />}
          >
            {p && (
              <Suspense fallback={<Skeleton className="h-[150px]" />}>
                <PlatformBars data={p.platforms} />
              </Suspense>
            )}
          </ChartFrame>
        </div>

        <div className="min-[720px]:col-span-2 min-[1280px]:col-span-4">
          <Card title={<h2 className="t-card flex items-center gap-2"><CalendarClock size={16} strokeWidth={1.75} aria-hidden /> Next gate deadline</h2>} className="h-full" updatedAt={p?.generated_at}>
            {data.isLoading ? (
              <Skeleton className="h-24" />
            ) : p?.next_gate ? (
              <div className="flex flex-col gap-2" data-testid="next-gate">
                <span className="t-kpi" title={timestamp(p.next_gate.due_at)}>
                  {Math.max(0, Math.ceil((new Date(p.next_gate.due_at).getTime() - clockNow()) / 864e5))} days
                </span>
                <span className="t-body">
                  {label(p.next_gate.kind)}: <button type="button" className="t-card text-accent hover:underline" onClick={() => openApp(p.next_gate!.app_id)}>{p.next_gate.name}</button>
                </span>
                <span className="t-label text-muted" title={timestamp(p.next_gate.due_at)}>
                  Due {relative(p.next_gate.due_at)} <ProvenanceBadge label="FIXTURE" />
                </span>
              </div>
            ) : (
              <p className="t-body text-muted">No approvals expire and no reviews are scheduled.</p>
            )}
          </Card>
        </div>

        <div className="min-[720px]:col-span-2 min-[1280px]:col-span-12">
          <Catalog onOpen={openApp} />
        </div>
      </div>

      <AppDrawer appId={f.get("app") || null} onClose={() => f.set({ app: null })} />
      <AssistDrawer open={f.get("assist") === "1"} onClose={() => f.set({ assist: null })} />
      <SpendDrawer open={f.get("spend") === "1"} onClose={() => f.set({ spend: null })} platform={f.platform} />
      <span className="sr-only">{p ? `${compact(p.secondary.total_apps.value ?? 0)} apps loaded` : ""}</span>
    </>
  );
}
