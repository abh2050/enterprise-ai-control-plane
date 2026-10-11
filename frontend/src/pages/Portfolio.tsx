import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { get, label, type AppCard, type PortfolioSummary } from "../api";
import {
  EmptyState,
  Loading,
  MetricTile,
  MetricValue,
  PageHeader,
  ProvenanceBadge,
  QueryError,
  Section,
} from "../components/ui";

export default function Portfolio() {
  const summary = useQuery({
    queryKey: ["portfolio"],
    queryFn: () => get<PortfolioSummary>("/portfolio/summary"),
  });
  const apps = useQuery({ queryKey: ["apps"], queryFn: () => get<AppCard[]>("/apps") });

  return (
    <>
      <PageHeader
        title="Portfolio"
        summary="Every AI application in the organization, what it costs, and where a decision is needed."
      />
      {summary.error ? (
        <QueryError error={summary.error} />
      ) : !summary.data ? (
        <Loading />
      ) : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-7">
          <MetricTile title="Total apps" metric={summary.data.total_apps} />
          <MetricTile title="In production" metric={summary.data.apps_in_production} />
          <MetricTile title="Stalled > 30 days" metric={summary.data.apps_stalled} />
          <MetricTile title="Monthly model spend" metric={summary.data.monthly_model_spend_usd} />
          <MetricTile
            title="Estimated monthly value"
            metric={summary.data.estimated_monthly_value_usd}
            hint={
              summary.data.estimated_monthly_value_usd.value === null
                ? "No business cases recorded"
                : undefined
            }
          />
          <MetricTile title="Open incidents" metric={summary.data.open_incidents} to="/incidents" />
          <MetricTile title="Approvals waiting" metric={summary.data.approvals_waiting} to="/reviews" />
        </div>
      )}

      <Section title="Investment matrix">
        <EmptyState
          title="Cost versus value needs business cases"
          missing="Monthly value estimates (ASSUMPTION) for each app."
          action="Owners record a business case in the lifecycle. The matrix, attention queue, and platform breakdown arrive in M4 with the 40-app synthetic registry."
        />
      </Section>

      <Section title="Catalog">
        {apps.error ? (
          <QueryError error={apps.error} />
        ) : !apps.data ? (
          <Loading />
        ) : apps.data.length === 0 ? (
          <EmptyState
            title="No applications registered"
            missing="Registry records."
            action="Run `cp importregistry` with a CSV export, or load the synthetic seed (M4)."
          />
        ) : (
          <div className="overflow-x-auto rounded-lg border border-line bg-surface">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="border-b border-line text-xs text-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">App</th>
                  <th className="px-4 py-2 font-medium">Owner</th>
                  <th className="px-4 py-2 font-medium">Platform</th>
                  <th className="px-4 py-2 font-medium">Stage</th>
                  <th className="px-4 py-2 font-medium">Risk</th>
                  <th className="px-4 py-2 text-right font-medium">Days in stage</th>
                  <th className="px-4 py-2 text-right font-medium">Monthly spend</th>
                </tr>
              </thead>
              <tbody>
                {apps.data.map((a) => (
                  <tr key={a.app_id} className="border-b border-line last:border-0">
                    <td className="px-4 py-2">
                      <Link className="font-medium hover:text-accent" to={`/apps/${a.app_id}`}>
                        {a.name}
                      </Link>{" "}
                      <ProvenanceBadge label={a.provenance} />
                    </td>
                    <td className="px-4 py-2 text-muted">{a.owner ?? "No owner"}</td>
                    <td className="px-4 py-2">{label(a.platform)}</td>
                    <td className="px-4 py-2">{label(a.stage)}</td>
                    <td className="px-4 py-2">{label(a.risk_tier)}</td>
                    <td className="px-4 py-2 text-right">
                      <MetricValue metric={a.days_in_stage} />
                    </td>
                    <td className="px-4 py-2 text-right">
                      <MetricValue metric={a.monthly_spend_usd} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </>
  );
}
