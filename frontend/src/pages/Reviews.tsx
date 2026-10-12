// Reviews (console spec Section 9): pending gate approvals and routed cases.
import { useMutation, useQuery } from "@tanstack/react-query";
import { Lock } from "lucide-react";
import { useState } from "react";
import { useSession } from "../components/Shell";
import { Button, Card, EmptyState, HeaderBand, Input, ModuleError, Skeleton, StatusText, useToast } from "../components/ui";
import { api } from "../lib/api";
import { label } from "../lib/format";
import { useApplyAppEvent } from "../lib/state";

interface GateItem {
  app_id: string;
  name: string;
  gate: string;
  risk_tier: string;
  submitted_by: string | null;
  owner: string | null;
  evidence: { business_problem: string; business_case: Record<string, { value?: number; unit?: string } | string> | null; platform: string };
  rubric: string[];
  can_decide: boolean;
  blocked_reason: string | null;
}

function GateCard({ item }: { item: GateItem }) {
  const { readOnly } = useSession();
  const toast = useToast();
  const apply = useApplyAppEvent();
  const [reason, setReason] = useState("");
  const decide = useMutation({
    mutationFn: (decision: "approve" | "reject") => api.post(`/apps/${item.app_id}/gates/${item.gate}`, { decision, reason }),
    onSuccess: (_, decision) => {
      apply({ app_id: item.app_id });
      toast({ kind: "success", message: `${label(item.gate)} gate ${decision}d for ${item.name}` });
    },
    onError: (e: Error) => toast({ kind: "error", message: e.message }),
  });
  const disabled = readOnly || !item.can_decide;
  const value = item.evidence.business_case?.monthly_value_usd as { value?: number } | undefined;
  return (
    <Card title={`${item.name}: ${label(item.gate)} review`} className={disabled ? "opacity-80" : undefined}>
      <div className="grid gap-4 min-[1024px]:grid-cols-2">
        <div>
          <h3 className="t-label mb-1 text-muted">Evidence</h3>
          <p className="t-body">{item.evidence.business_problem}</p>
          <p className="t-label mt-2 text-muted">
            {label(item.evidence.platform)} · {label(item.risk_tier)} risk · submitted by {item.submitted_by ?? "unknown"}
            {value?.value !== undefined && ` · estimated value $${value.value.toLocaleString()} per month (ASSUMPTION)`}
          </p>
        </div>
        <div>
          <h3 className="t-label mb-1 text-muted">Rubric</h3>
          <ul className="t-body list-disc pl-4">
            {item.rubric.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      </div>
      {item.blocked_reason && (
        <div className="mt-4">
          <StatusText tone="info" icon={Lock}>
            {item.blocked_reason}
          </StatusText>
        </div>
      )}
      <form
        className="mt-4 flex flex-wrap items-end gap-2"
        onSubmit={(e) => e.preventDefault()}
        aria-disabled={disabled}
      >
        <label className="t-label flex min-w-60 flex-1 flex-col gap-1 text-muted">
          Decision reason
          <Input value={reason} disabled={disabled} onChange={(e) => setReason(e.target.value)} placeholder={disabled ? "Not available to you" : "Why approve or reject"} />
        </label>
        <Button variant="primary" disabled={disabled || !reason.trim()} loading={decide.isPending && decide.variables === "approve"} onClick={() => decide.mutate("approve")}>
          Approve
        </Button>
        <Button variant="danger" disabled={disabled || !reason.trim()} loading={decide.isPending && decide.variables === "reject"} onClick={() => decide.mutate("reject")}>
          Reject
        </Button>
      </form>
    </Card>
  );
}

export default function Reviews() {
  const data = useQuery({ queryKey: ["reviews"], queryFn: () => api.get<{ gates: GateItem[]; cases: unknown[] }>("/reviews/pending") });
  return (
    <>
      <HeaderBand page="reviews" title="Reviews" summary="Pending gate approvals and routed cases. The person who submitted an item can never approve it." />
      {data.isLoading ? (
        <Skeleton className="h-64" />
      ) : data.error ? (
        <ModuleError error={data.error} onRetry={() => void data.refetch()} />
      ) : (
        <div className="flex flex-col gap-6">
          <section aria-labelledby="gates-h">
            <h2 id="gates-h" className="t-card mb-3">
              Gate approvals ({data.data?.gates.length ?? 0})
            </h2>
            {data.data?.gates.length ? (
              <div className="flex flex-col gap-4">
                {data.data.gates.map((g) => (
                  <GateCard key={`${g.app_id}-${g.gate}`} item={g} />
                ))}
              </div>
            ) : (
              <EmptyState illustration="no-reviews" title="No gates are waiting" missing="Apps reach review gates after their owner submits a complete business case." />
            )}
          </section>
          <section aria-labelledby="cases-h">
            <h2 id="cases-h" className="t-card mb-3">
              Routed cases
            </h2>
            <EmptyState illustration="no-reviews" title="No routed cases yet" missing="Support Triage cases routed to review appear here once shadow replay runs (milestone M5)." />
          </section>
        </div>
      )}
    </>
  );
}
