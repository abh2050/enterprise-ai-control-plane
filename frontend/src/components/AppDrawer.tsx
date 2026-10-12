// App drawer (console spec Section 9, Applications page): identity, key facts, stage
// timeline, open incidents, and a governance notes composer fixed to the bottom.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, Pencil, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { api, ApiError, type AppDetailData, type Note } from "../lib/api";
import { label, relative, timestamp } from "../lib/format";
import { track } from "../lib/state";
import { useSession } from "./Shell";
import { Button, Drawer, HealthPill, MetricInline, ModuleError, ProvenanceBadge, Skeleton, Textarea, useToast } from "./ui";

const DRAFT_TTL = 24 * 60 * 60 * 1000;
const EDIT_WINDOW = 15 * 60 * 1000;

function draftKey(appId: string) {
  return `cp.noteDraft.${appId}`;
}
function loadDraft(appId: string): string {
  try {
    const raw = localStorage.getItem(draftKey(appId));
    if (!raw) return "";
    const { text, savedAt } = JSON.parse(raw) as { text: string; savedAt: number };
    return Date.now() - savedAt < DRAFT_TTL ? text : "";
  } catch {
    return "";
  }
}
function saveDraft(appId: string, text: string) {
  try {
    if (text) localStorage.setItem(draftKey(appId), JSON.stringify({ text, savedAt: Date.now() }));
    else localStorage.removeItem(draftKey(appId));
  } catch {
    // drafts are a convenience only
  }
}

function NoteItem({ note, appId }: { note: Note; appId: string }) {
  const { me } = useSession();
  const qc = useQueryClient();
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(note.text);
  const canEdit = me?.email === note.author && Date.now() - new Date(note.created_at).getTime() < EDIT_WINDOW;
  const canDelete = me?.email === note.author || me?.role === "governance_admin";
  const refresh = () => qc.invalidateQueries({ queryKey: ["app", appId] });
  const edit = useMutation({
    mutationFn: () => api.patch(`/notes/${encodeURIComponent(note.note_id)}`, { text }),
    onSuccess: () => {
      setEditing(false);
      void refresh();
    },
    onError: (e: Error) => toast({ kind: "error", message: e.message }),
  });
  const remove = useMutation({
    mutationFn: (reason: string) => api.post(`/notes/${encodeURIComponent(note.note_id)}/delete`, { reason }),
    onSuccess: () => void refresh(),
    onError: (e: Error) => toast({ kind: "error", message: e.message }),
  });
  return (
    <li className="rounded-lg border border-line p-3">
      <div className="t-label flex items-center justify-between text-muted">
        <span>
          {note.author} · <span title={timestamp(note.created_at)}>{relative(note.created_at)}</span>
          {note.edited_at && <span title={`${note.history.length} earlier version(s) kept`}> · edited</span>}
        </span>
        <span className="flex gap-1">
          {canEdit && !editing && (
            <button type="button" aria-label="Edit note" title="Edit note (15 minutes after saving)" onClick={() => setEditing(true)} className="rounded p-1 hover:bg-raised">
              <Pencil size={16} strokeWidth={1.75} aria-hidden />
            </button>
          )}
          {canDelete && (
            <button
              type="button"
              aria-label="Delete note"
              title="Delete note (requires a reason)"
              className="rounded p-1 hover:bg-raised"
              onClick={() => {
                const reason = window.prompt("Reason for deleting this note");
                if (reason?.trim()) remove.mutate(reason);
              }}
            >
              <Trash2 size={16} strokeWidth={1.75} aria-hidden />
            </button>
          )}
        </span>
      </div>
      {editing ? (
        <div className="mt-2 flex flex-col gap-2">
          <Textarea value={text} maxLength={5000} onChange={(e) => setText(e.target.value)} aria-label="Edit note" rows={3} />
          <div className="flex gap-2">
            <Button variant="primary" loading={edit.isPending} onClick={() => edit.mutate()}>
              Save
            </Button>
            <Button variant="ghost" onClick={() => setEditing(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <p className="t-body mt-1 whitespace-pre-wrap">{note.text}</p>
      )}
    </li>
  );
}

function Composer({ appId }: { appId: string }) {
  const { readOnly } = useSession();
  const qc = useQueryClient();
  const toast = useToast();
  const [text, setText] = useState(() => loadDraft(appId));
  const key = useRef(crypto.randomUUID());
  useEffect(() => saveDraft(appId, text), [appId, text]);
  const save = useMutation({
    mutationFn: () => api.post<{ created: boolean }>(`/apps/${appId}/notes`, { text, idempotency_key: key.current }),
    onSuccess: () => {
      setText("");
      saveDraft(appId, "");
      key.current = crypto.randomUUID();
      track("note_created", "app_drawer", appId);
      void qc.invalidateQueries({ queryKey: ["app", appId] });
      toast({ kind: "success", message: "Note saved" });
    },
    onError: (e: Error) => toast({ kind: "error", message: e.message }),
  });
  if (readOnly) return <p className="t-label text-muted">Your role can read notes but not add them.</p>;
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (text.trim() && !save.isPending) save.mutate();
      }}
      className="flex flex-col gap-2"
    >
      <Textarea
        value={text}
        maxLength={5000}
        rows={3}
        aria-label="Governance note"
        placeholder="Add a governance note. Ctrl or Cmd + Enter to save."
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            if (text.trim() && !save.isPending) save.mutate();
          }
        }}
      />
      <div className="t-label flex items-center justify-between text-muted">
        <span>{text.length.toLocaleString()} / 5,000 · drafts kept on this device for 24 hours</span>
        <Button type="submit" variant="primary" loading={save.isPending} disabled={!text.trim()}>
          Save note
        </Button>
      </div>
    </form>
  );
}

export function AppDrawer({ appId, onClose }: { appId: string | null; onClose: () => void }) {
  const detail = useQuery({
    queryKey: ["app", appId],
    queryFn: () => api.get<AppDetailData>(`/apps/${appId}`),
    enabled: !!appId,
  });
  useEffect(() => {
    if (appId) track("app_drawer_opened", "drawer", appId);
  }, [appId]);
  const d = detail.data;
  const forbidden = detail.error instanceof ApiError && detail.error.status === 403;
  return (
    <Drawer
      open={!!appId}
      onClose={onClose}
      width={480}
      title={
        d ? (
          <div>
            <h2 className="t-page">{d.app.name}</h2>
            <div className="t-label mt-1 flex flex-wrap items-center gap-2 text-muted">
              <span>{d.card.business_unit}</span>·<span>{label(d.card.platform)}</span>·<span>{label(d.card.stage)}</span>
              <ProvenanceBadge label={(d.card.provenance === "SYNTHETIC" ? "SYNTHETIC" : "IMPORTED") as "SYNTHETIC"} />
            </div>
          </div>
        ) : (
          "Application"
        )
      }
      footer={appId && d ? <Composer appId={appId} /> : undefined}
    >
      {detail.isLoading ? (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-6 w-2/3" />
          <Skeleton className="h-24" />
          <Skeleton className="h-40" />
        </div>
      ) : forbidden ? (
        <p className="t-body text-muted">Your role can see this app in the portfolio but not its details.</p>
      ) : detail.error ? (
        <ModuleError error={detail.error} onRetry={() => void detail.refetch()} />
      ) : d ? (
        <div className="flex flex-col gap-6">
          <div className="flex flex-wrap gap-2">
            <Link to={`/apps/${d.app.app_id}`} className="m-hover inline-flex min-h-9 items-center gap-2 rounded-lg bg-accent px-4 t-card text-on-accent hover:bg-accent-strong">
              <ExternalLink size={16} strokeWidth={1.75} aria-hidden /> Open details
            </Link>
            <Link to={`/pipeline?stage=${d.card.stage}`} className="m-hover inline-flex min-h-9 items-center rounded-lg border border-line-strong px-4 t-card hover:bg-raised">
              Show on pipeline
            </Link>
          </div>
          <p className="t-body text-muted">{d.app.business_problem}</p>
          <dl className="grid grid-cols-2 gap-4">
            {[
              ["Owner", d.card.owner ?? "No owner"],
              ["Risk tier", label(d.card.risk_tier)],
              ["Days in stage", <MetricInline key="d" metric={d.card.days_in_stage} />],
              ["Monthly spend", <MetricInline key="s" metric={d.card.monthly_spend_usd} />],
              ["Estimated value", <MetricInline key="v" metric={d.card.estimated_value_usd} />],
              ["Health", <HealthPill key="h" health={d.card.health} rule={d.card.health_rule} />],
              ["Next gate", d.card.next_gate ? `${label(d.card.next_gate.kind)} ${relative(d.card.next_gate.due_at)}` : "None scheduled"],
              ["Assist score", `${Math.round(d.card.assist_score * 100)} / 100`],
            ].map(([k, v]) => (
              <div key={String(k)}>
                <dt className="t-label text-muted">{k}</dt>
                <dd className="t-body mt-1">{v}</dd>
              </div>
            ))}
          </dl>
          {d.incidents.filter((i) => i.status === "open").length > 0 && (
            <section>
              <h3 className="t-card mb-2">Open incidents</h3>
              <ul className="flex flex-col gap-2">
                {d.incidents
                  .filter((i) => i.status === "open")
                  .map((i) => (
                    <li key={i.incident_id} className="t-body rounded-lg border border-line p-3">
                      {label(i.signal)}: observed {i.observed} vs threshold {i.threshold} · opened <span title={timestamp(i.opened_at)}>{relative(i.opened_at)}</span>
                    </li>
                  ))}
              </ul>
            </section>
          )}
          <section>
            <h3 className="t-card mb-2">Stage timeline</h3>
            <ol className="flex flex-col gap-2 border-l border-line pl-4">
              {d.events
                .slice()
                .reverse()
                .map((e) => (
                  <li key={e.event_id} className="t-body">
                    <span className="t-card">{e.to_stage && e.kind === "stage_change" ? `${label(e.from_stage ?? "")} → ${label(e.to_stage)}` : label(e.kind)}</span>
                    <span className="t-label block text-muted">
                      {e.actor} · <span title={timestamp(e.created_at)}>{relative(e.created_at)}</span> · {e.reason}
                    </span>
                  </li>
                ))}
            </ol>
          </section>
          <section>
            <h3 className="t-card mb-2">Governance notes</h3>
            {d.notes.length === 0 ? (
              <p className="t-body text-muted">No notes yet.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {d.notes.map((n) => (
                  <NoteItem key={n.note_id} note={n} appId={d.app.app_id} />
                ))}
              </ul>
            )}
          </section>
        </div>
      ) : null}
    </Drawer>
  );
}
