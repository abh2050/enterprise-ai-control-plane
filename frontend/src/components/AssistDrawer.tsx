// Governance Assist drawer (console spec Section 9). Assist never changes a record
// silently: every action needs explicit confirmation, and failures stay visible.
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, type AssistReason, type Metric } from "../lib/api";
import { label, money, relative, timestamp } from "../lib/format";
import { track, useApplyAppEvent } from "../lib/state";
import { useSession } from "./Shell";
import { Button, Drawer, Input, ModuleError, ProvenanceBadge, Skeleton, Textarea, useToast } from "./ui";

interface AssistRow {
  app_id: string;
  name: string;
  stage: string;
  version: number;
  score: number;
  flagged: boolean;
  reasons: AssistReason[];
  spend: Metric;
  value: Metric;
  scored_at: string;
}
interface AssistData {
  threshold: number;
  rows: AssistRow[];
  rules: Record<string, { points: number; label: string }>;
  scored_at: string | null;
}

type Pending = { kind: "schedule" | "dismiss" | "safe"; row: AssistRow; code?: string } | null;

function ActionForm({ pending, onDone, onCancel }: { pending: NonNullable<Pending>; onDone: () => void; onCancel: () => void }) {
  const toast = useToast();
  const apply = useApplyAppEvent();
  const inTwoWeeks = new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10);
  const [date, setDate] = useState(inTwoWeeks);
  const [text, setText] = useState(pending.kind === "schedule" ? `Review ${pending.row.name}: ${pending.row.reasons[0]?.label ?? ""}` : "");
  const m = useMutation({
    mutationFn: () => {
      const id = pending.row.app_id;
      if (pending.kind === "schedule")
        return api.post(`/assist/${id}/schedule-review`, { review_at: `${date}T09:00:00+00:00`, expected_version: pending.row.version, note: text });
      if (pending.kind === "dismiss") return api.post(`/assist/${id}/dismiss`, { code: pending.code, reason: text });
      return api.post(`/assist/${id}/mark-safe`, { note: text });
    },
    onSuccess: () => {
      track("assist_action_completed", "assist_drawer", pending.row.app_id);
      apply({ app_id: pending.row.app_id });
      toast({ kind: "success", message: pending.kind === "schedule" ? "Review scheduled" : pending.kind === "dismiss" ? "Reason dismissed for 7 days" : "Marked safe" });
      onDone();
    },
  });
  const title = { schedule: "Schedule a review", dismiss: "Dismiss this reason", safe: "Mark this app safe" }[pending.kind];
  return (
    <form
      className="mt-3 flex flex-col gap-3 rounded-lg border border-accent bg-accent-soft p-4"
      onSubmit={(e) => {
        e.preventDefault();
        m.mutate();
      }}
    >
      <h4 className="t-card">{title}</h4>
      {pending.kind === "schedule" && (
        <label className="t-label flex flex-col gap-1 text-muted">
          Review date
          <Input type="date" value={date} min={new Date().toISOString().slice(0, 10)} onChange={(e) => setDate(e.target.value)} />
        </label>
      )}
      <label className="t-label flex flex-col gap-1 text-muted">
        {pending.kind === "schedule" ? "Note (prefilled, editable)" : pending.kind === "dismiss" ? "Reason (required)" : "Note for the audit trail (required)"}
        <Textarea rows={2} value={text} onChange={(e) => setText(e.target.value)} required={pending.kind !== "schedule"} />
      </label>
      <p className="t-label text-muted">Nothing is saved until you confirm. This writes an audit event.</p>
      {m.error && <ModuleError error={m.error} onRetry={() => m.mutate()} compact />}
      <div className="flex gap-2">
        <Button type="submit" variant="primary" loading={m.isPending} disabled={pending.kind !== "schedule" && !text.trim()}>
          Confirm
        </Button>
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

export function AssistDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { readOnly, me } = useSession();
  const data = useQuery({ queryKey: ["assist"], queryFn: () => api.get<AssistData>("/assist"), enabled: open });
  const [pending, setPending] = useState<Pending>(null);
  useEffect(() => {
    if (open) track("assist_opened", "portfolio");
  }, [open]);
  const flagged = data.data?.rows.filter((r) => r.score > 0) ?? [];
  const atRisk = data.data?.rows.filter((r) => r.score >= (data.data?.threshold ?? 0.65)) ?? [];
  const valueAtRisk = atRisk.reduce((s, r) => s + (r.value.value ?? 0), 0);
  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={420}
      dirty={pending !== null}
      title={
        <div>
          <h2 className="t-page">Governance Assist</h2>
          {data.data && (
            <p className="t-label mt-1 flex flex-wrap items-center gap-2 text-muted">
              {money(valueAtRisk)} value at risk <ProvenanceBadge label="ASSUMPTION" /> · {atRisk.length} apps at or above {data.data.threshold} · scored{" "}
              <span title={timestamp(data.data.scored_at)}>{relative(data.data.scored_at)}</span>
            </p>
          )}
        </div>
      }
      footer={
        <details className="t-label text-muted">
          <summary className="cursor-pointer">How scores work</summary>
          <p className="mt-2">Deterministic rules from configs/lifecycle.yaml. Score = points / 100, clamped to 0..1; 0.65 or more needs a decision.</p>
          <ul className="mt-2 grid grid-cols-2 gap-1">
            {data.data &&
              Object.entries(data.data.rules).map(([code, r]) => (
                <li key={code}>
                  {r.points > 0 ? "+" : ""}
                  {r.points}: {r.label}
                </li>
              ))}
          </ul>
        </details>
      }
    >
      {data.isLoading ? (
        <Skeleton className="h-64" />
      ) : data.error ? (
        <ModuleError error={data.error} onRetry={() => void data.refetch()} />
      ) : (
        <ul className="flex flex-col gap-3">
          {flagged.map((r) => (
            <li key={r.app_id} className="rounded-lg border border-line p-4" data-testid={`assist-row-${r.app_id}`}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="t-card">{r.name}</span>
                  <span className="t-label block text-muted">
                    {label(r.stage)} · spend {money(r.spend.value)} <ProvenanceBadge label={r.spend.provenance} />
                  </span>
                </div>
                <span className={`t-card ${r.score >= (data.data?.threshold ?? 0.65) ? "text-danger" : "text-warning"}`} aria-label={`Score ${r.score}`}>
                  {Math.round(r.score * 100)}
                </span>
              </div>
              <ul className="mt-2 flex flex-col gap-1">
                {r.reasons.map((x) => (
                  <li key={x.code} className="t-label flex items-start justify-between gap-2">
                    <span>
                      {x.points > 0 ? "+" : ""}
                      {x.points} {x.label}
                      <span className="block font-normal text-muted">Evidence: {x.evidence}</span>
                      {x.action && <span className="block font-normal text-muted">Next: {x.action}</span>}
                    </span>
                    {!readOnly && x.points > 0 && (
                      <button type="button" className="shrink-0 underline" onClick={() => setPending({ kind: "dismiss", row: r, code: x.code })}>
                        Dismiss
                      </button>
                    )}
                  </li>
                ))}
              </ul>
              {!readOnly && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button variant="primary" className="min-h-8" onClick={() => setPending({ kind: "schedule", row: r })}>
                    Schedule review
                  </Button>
                  {me?.role === "governance_admin" && (
                    <Button className="min-h-8" onClick={() => setPending({ kind: "safe", row: r })}>
                      Mark safe
                    </Button>
                  )}
                </div>
              )}
              {pending?.row.app_id === r.app_id && <ActionForm pending={pending} onDone={() => setPending(null)} onCancel={() => setPending(null)} />}
            </li>
          ))}
          {flagged.length === 0 && <p className="t-body text-muted">No app needs attention right now.</p>}
        </ul>
      )}
    </Drawer>
  );
}
