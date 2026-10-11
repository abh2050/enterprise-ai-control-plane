import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { get, label, STAGES, type AppCard } from "../api";
import { Loading, MetricValue, PageHeader, QueryError, StatusPill } from "../components/ui";

const STALL_DAYS = 30;

export default function Pipeline() {
  const apps = useQuery({ queryKey: ["apps"], queryFn: () => get<AppCard[]>("/apps") });
  return (
    <>
      <PageHeader
        title="Pipeline"
        summary="One column per lifecycle stage. Moving cards between stages arrives in M4, where the server validates every transition."
      />
      {apps.error ? (
        <QueryError error={apps.error} />
      ) : !apps.data ? (
        <Loading />
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-4">
          {STAGES.map((stage) => {
            const cards = apps.data.filter((a) => a.stage === stage);
            return (
              <section
                key={stage}
                aria-label={label(stage)}
                className="w-64 shrink-0 rounded-lg border border-line bg-surface-2 p-2"
              >
                <h2 className="flex items-center justify-between px-1 pb-2 text-xs font-semibold text-muted">
                  {label(stage)}
                  <span>{cards.length}</span>
                </h2>
                <ul className="space-y-2">
                  {cards.map((a) => {
                    const days = a.days_in_stage.value ?? 0;
                    return (
                      <li key={a.app_id} className="animate-enter rounded-md border border-line bg-surface p-3 text-sm">
                        <Link to={`/apps/${a.app_id}`} className="font-medium hover:text-accent">
                          {a.name}
                        </Link>
                        <div className="mt-1 text-xs text-muted">{a.owner ?? "No owner"}</div>
                        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted">
                          <span>{label(a.platform)}</span>
                          <span>{label(a.risk_tier)} risk</span>
                        </div>
                        <div className="mt-2 flex items-center justify-between text-xs">
                          <MetricValue metric={a.days_in_stage} />
                          {days > STALL_DAYS && stage !== "retired" && (
                            <StatusPill status="amber" text="Stalled" />
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </section>
            );
          })}
        </div>
      )}
    </>
  );
}
