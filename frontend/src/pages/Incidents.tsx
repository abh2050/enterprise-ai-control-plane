import { useQuery } from "@tanstack/react-query";
import { get, type Incident } from "../api";
import { EmptyState, Loading, PageHeader, QueryError, StatusPill } from "../components/ui";

export default function Incidents() {
  const incidents = useQuery({ queryKey: ["incidents"], queryFn: () => get<Incident[]>("/incidents") });
  return (
    <>
      <PageHeader
        title="Incidents"
        summary="Open and closed incidents, with timelines and the actions taken."
      />
      {incidents.error ? (
        <QueryError error={incidents.error} />
      ) : !incidents.data ? (
        <Loading />
      ) : incidents.data.length === 0 ? (
        <EmptyState
          title="No incidents"
          missing="Monitoring signals and alert thresholds."
          action="Monitoring opens incidents when a signal breaches its threshold (M5). The drill in M5 produces a FIXTURE incident."
        />
      ) : (
        <ul className="space-y-2">
          {incidents.data.map((i) => (
            <li key={i.incident_id} className="rounded-lg border border-line bg-surface p-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">{i.signal}</span>
                <StatusPill status={i.status === "open" ? "red" : "green"} text={i.status} />
              </div>
              <div className="mt-1 text-xs text-muted">
                {i.app_id} · opened {new Date(i.opened_at).toLocaleString()}
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
