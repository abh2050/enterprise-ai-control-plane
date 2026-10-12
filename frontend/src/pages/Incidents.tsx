// Incidents (console spec Section 9).
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, OctagonAlert } from "lucide-react";
import { Card, EmptyState, HeaderBand, ModuleError, ProvenanceBadge, Skeleton, StatusText } from "../components/ui";
import { api, type Incident } from "../lib/api";
import { label, relative, timestamp } from "../lib/format";

export default function Incidents() {
  const data = useQuery({ queryKey: ["incidents"], queryFn: () => api.get<Incident[]>("/incidents") });
  const open = data.data?.filter((i) => i.status === "open") ?? [];
  const closed = data.data?.filter((i) => i.status !== "open") ?? [];
  const list = (items: Incident[]) => (
    <ul className="flex flex-col gap-4">
      {items.map((i) => (
        <li key={i.incident_id}>
          <Card
            title={
              <div className="flex flex-wrap items-center gap-3">
                <h3 className="t-card">
                  {label(i.signal)} on {i.app_id}
                </h3>
                {i.status === "open" ? (
                  <StatusText tone="danger" icon={OctagonAlert}>
                    Open
                  </StatusText>
                ) : (
                  <StatusText tone="healthy" icon={CheckCircle2}>
                    {label(i.status)}
                  </StatusText>
                )}
                <ProvenanceBadge label={(i.provenance as "SYNTHETIC") ?? "FIXTURE"} />
              </div>
            }
          >
            <dl className="t-body grid grid-cols-2 gap-3 min-[720px]:grid-cols-4">
              <div>
                <dt className="t-label text-muted">Threshold</dt>
                <dd>{i.threshold}</dd>
              </div>
              <div>
                <dt className="t-label text-muted">Observed</dt>
                <dd>{i.observed}</dd>
              </div>
              <div>
                <dt className="t-label text-muted">Opened</dt>
                <dd title={timestamp(i.opened_at)}>{relative(i.opened_at)}</dd>
              </div>
              <div>
                <dt className="t-label text-muted">Closed</dt>
                <dd title={timestamp(i.closed_at)}>{i.closed_at ? relative(i.closed_at) : "—"}</dd>
              </div>
            </dl>
            <h4 className="t-label mt-4 mb-1 text-muted">Timeline and actions</h4>
            <ol className="t-body list-decimal pl-5">
              <li>
                Opened <span title={timestamp(i.opened_at)}>{relative(i.opened_at)}</span>: {label(i.signal)} observed {i.observed} against threshold {i.threshold}
              </li>
              {i.actions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ol>
          </Card>
        </li>
      ))}
    </ul>
  );
  return (
    <>
      <HeaderBand page="incidents" variant={open.length ? "incident" : "default"} title="Incidents" summary="Open and closed incidents, with the signal, threshold, observed value, timeline, and actions taken." />
      {data.isLoading ? (
        <Skeleton className="h-64" />
      ) : data.error ? (
        <ModuleError error={data.error} onRetry={() => void data.refetch()} />
      ) : data.data?.length === 0 ? (
        <EmptyState illustration="no-incidents" title="No incidents" missing="Monitoring opens an incident when a daily signal crosses its alert threshold." />
      ) : (
        <div className="flex flex-col gap-6">
          <section aria-labelledby="open-h">
            <h2 id="open-h" className="t-card mb-3">
              Open ({open.length})
            </h2>
            {open.length ? list(open) : <p className="t-body text-muted">No open incidents.</p>}
          </section>
          <section aria-labelledby="closed-h">
            <h2 id="closed-h" className="t-card mb-3">
              Closed ({closed.length})
            </h2>
            {closed.length ? list(closed) : <p className="t-body text-muted">No closed incidents yet.</p>}
          </section>
        </div>
      )}
    </>
  );
}
