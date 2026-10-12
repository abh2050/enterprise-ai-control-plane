// Applications directory (console spec Section 9).
import { useQuery } from "@tanstack/react-query";
import { AppDrawer } from "../components/AppDrawer";
import { DataTable, EmptyState, HeaderBand, HealthPill, Input, MetricInline, ModuleError, ProvenanceBadge, Select, Skeleton } from "../components/ui";
import { api, query, STAGES, type AppCard } from "../lib/api";
import { label, relative, timestamp } from "../lib/format";
import { useUrlFilters } from "../lib/state";

export default function Applications() {
  const f = useUrlFilters();
  const params = { platform: f.platform, q: f.get("q"), owner: f.get("owner"), stage: f.get("stage"), health: f.get("health"), sort: f.get("sort", "recent") };
  const apps = useQuery({ queryKey: ["apps", "directory", params], queryFn: () => api.get<AppCard[]>(`/apps${query(params)}`) });
  const all = useQuery({ queryKey: ["apps", "all", f.platform], queryFn: () => api.get<AppCard[]>(`/apps${query({ platform: f.platform })}`) });
  const owners = [...new Set((all.data ?? []).map((c) => c.owner).filter(Boolean))] as string[];
  return (
    <>
      <HeaderBand page="applications" title="Applications" summary="Every registered app with its owner, stage, spend, and next gate. Open an app to see its timeline and governance notes.">
        <ProvenanceBadge label="SYNTHETIC" />
      </HeaderBand>
      <div className="mb-4 grid grid-cols-1 gap-3 min-[720px]:grid-cols-5">
        <Input aria-label="Search applications" placeholder="Search name, owner, problem" defaultValue={params.q} onChange={(e) => f.set({ q: e.target.value || null })} className="min-[720px]:col-span-2" />
        <Select label="Owner" value={params.owner} onChange={(v) => f.set({ owner: v || null })} options={[{ value: "", label: "All owners" }, ...owners.map((o) => ({ value: o, label: o }))]} />
        <Select label="Stage" value={params.stage} onChange={(v) => f.set({ stage: v || null })} options={[{ value: "", label: "All stages" }, ...STAGES.map((s) => ({ value: s, label: label(s) }))]} />
        <Select label="Health" value={params.health} onChange={(v) => f.set({ health: v || null })} options={[{ value: "", label: "All health" }, ...["healthy", "warning", "danger"].map((s) => ({ value: s, label: label(s) }))]} />
      </div>
      {apps.isLoading ? (
        <Skeleton className="h-96" />
      ) : apps.error ? (
        <ModuleError error={apps.error} onRetry={() => void apps.refetch()} />
      ) : apps.data?.length === 0 ? (
        <EmptyState illustration="no-apps" title="No applications match" missing="Clear the filters, or import your organization's app list with cp importregistry." />
      ) : (
        <div className="relative overflow-x-auto rounded-xl border border-line bg-surface p-4">
          <DataTable
            caption="Applications"
            columns={["Name and business unit", "Owner", "Platform", "Stage", "Monthly spend", "Last activity", "Next gate", "Health"]}
            rows={(apps.data ?? []).map((a) => [
              <button key="n" type="button" onClick={() => f.set({ app: a.app_id })} className="text-left">
                <span className="t-card block hover:text-accent">{a.name}</span>
                <span className="t-label text-muted">{a.business_unit}</span>
              </button>,
              a.owner ?? "No owner",
              label(a.platform),
              label(a.stage),
              <MetricInline key="s" metric={a.monthly_spend_usd} />,
              <span key="l" title={timestamp(a.last_activity_at)}>
                {relative(a.last_activity_at)}
              </span>,
              a.next_gate ? (
                <span key="g" title={timestamp(a.next_gate.due_at)}>
                  {label(a.next_gate.kind)} {relative(a.next_gate.due_at)}
                </span>
              ) : (
                "—"
              ),
              <HealthPill key="h" health={a.health} rule={a.health_rule} />,
            ])}
          />
        </div>
      )}
      <AppDrawer appId={f.get("app") || null} onClose={() => f.set({ app: null })} />
    </>
  );
}
