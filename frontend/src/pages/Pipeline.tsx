// Pipeline board (console spec Section 9). Pointer and keyboard moves share one code path,
// so they send the same payload and produce the same audit event.
import { DndContext, DragOverlay, PointerSensor, useDraggable, useDroppable, useSensor, useSensors, type DragEndEvent, type DragMoveEvent, type DragStartEvent } from "@dnd-kit/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, MoreHorizontal } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { AppDrawer } from "../components/AppDrawer";
import { useSession } from "../components/Shell";
import { Button, Drawer, EmptyState, HeaderBand, Input, ModuleError, ProvenanceBadge, Select, Skeleton, StatusText, cx, useAnnouncer, useToast } from "../components/ui";
import { api, ApiError, query, STAGES, type AppCard, type AppEvent, type Stage } from "../lib/api";
import { label, money } from "../lib/format";
import { track, useApplyAppEvent, useUrlFilters } from "../lib/state";

type Move = { allowed: boolean; code: string | null; message: string | null; needs_reason: boolean };
type BoardCard = AppCard & { moves?: Record<string, Move> };
type Source = "drag" | "keyboard" | "menu";
interface Conflict {
  card: BoardCard;
  to: Stage;
  reason?: string;
  source: Source;
  current: Record<string, unknown> & { stage: Stage; version: number };
}

const EDGE = 48;
const MAX_SPEED = 24;

function initials(email: string | null) {
  return email ? email.slice(0, 2).toUpperCase() : "—";
}

function CardBody({ c }: { c: BoardCard }) {
  return (
    <>
      <div className="flex items-start justify-between gap-2">
        <span className="t-card line-clamp-2">{c.name}</span>
        {c.assist_score > 0 && (
          <span
            title={`Governance Assist score ${Math.round(c.assist_score * 100)}`}
            aria-label={`Assist score ${Math.round(c.assist_score * 100)}`}
            className={cx("mt-1 size-2.5 shrink-0 rounded-full", c.assist_flagged ? "bg-danger" : "bg-warning")}
          />
        )}
      </div>
      <div className="flex items-center gap-2">
        <span className="t-label flex size-6 items-center justify-center rounded-full bg-accent-soft text-accent" aria-hidden>
          {initials(c.owner)}
        </span>
        <span className="t-label truncate font-normal text-muted">{c.owner ?? "No owner"}</span>
      </div>
      <div className="t-label flex flex-wrap gap-x-3 gap-y-1 font-normal text-muted">
        <span>{label(c.platform)}</span>
        <span>{label(c.risk_tier)} risk</span>
        <span title={`${c.days_in_stage.value} days in stage (${c.days_in_stage.provenance})`}>{c.days_in_stage.value}d in stage</span>
      </div>
      {c.stall_warning && (
        <StatusText tone="warning" icon={AlertTriangle}>
          Over 30 days in stage
        </StatusText>
      )}
    </>
  );
}

function BoardCardView({
  c,
  moving,
  onKey,
  onMenu,
  disabled,
}: {
  c: BoardCard;
  moving: boolean;
  onKey: (e: React.KeyboardEvent, c: BoardCard) => void;
  onMenu: (c: BoardCard, action: "open" | "edit" | "move" | "archive") => void;
  disabled: boolean;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: c.app_id, disabled });
  const [menu, setMenu] = useState(false);
  return (
    <li className="relative">
      <div
        ref={setNodeRef}
        {...listeners}
        {...attributes}
        role="button"
        tabIndex={0}
        data-app={c.app_id}
        aria-roledescription="Movable app card"
        aria-describedby="pipeline-help"
        onKeyDown={(e) => onKey(e, c)}
        className={cx(
          "m-card flex min-h-36 flex-col gap-3 rounded-xl border bg-surface p-4 text-left",
          moving ? "border-accent ring-2 ring-accent" : "border-line",
          isDragging && "opacity-40",
          menu && "ring-2 ring-focus",
        )}
      >
        <CardBody c={c} />
      </div>
      <button
        type="button"
        aria-label={`Actions for ${c.name}`}
        title="Actions"
        aria-haspopup="menu"
        aria-expanded={menu}
        onClick={() => setMenu((m) => !m)}
        className="absolute right-2 bottom-2 flex size-8 items-center justify-center rounded-lg text-muted hover:bg-raised"
      >
        <MoreHorizontal size={16} strokeWidth={1.75} aria-hidden />
      </button>
      {menu && (
        <div role="menu" className="shadow-overlay absolute right-2 bottom-11 z-20 w-36 rounded-lg border border-line bg-overlay p-1" onMouseLeave={() => setMenu(false)}>
          {(["open", "edit", "move", "archive"] as const).map((a) => (
            <button
              key={a}
              role="menuitem"
              type="button"
              disabled={disabled && (a === "move" || a === "archive")}
              className="t-body flex w-full rounded px-3 py-2 text-left hover:bg-raised disabled:opacity-50"
              onClick={() => {
                setMenu(false);
                onMenu(c, a);
              }}
            >
              {label(a)}
            </button>
          ))}
        </div>
      )}
    </li>
  );
}

function Column({ stage, cards, valid, target, children }: { stage: Stage; cards: BoardCard[]; valid: boolean; target: boolean; children: React.ReactNode }) {
  const { setNodeRef, isOver } = useDroppable({ id: stage });
  const spend = cards.reduce((s, c) => s + (c.monthly_spend_usd.value ?? 0), 0);
  return (
    <section
      ref={setNodeRef}
      aria-label={`${label(stage)}: ${cards.length} apps`}
      data-stage={stage}
      className={cx(
        "m-hover flex w-[280px] shrink-0 flex-col rounded-xl border bg-raised",
        valid || target ? "border-2 border-accent bg-accent-soft" : "border-line",
        isOver && valid && "ring-2 ring-accent",
      )}
    >
      <header className="sticky top-0 z-10 flex h-12 items-center justify-between rounded-t-xl border-b border-line bg-raised px-4">
        <span className="t-card">{label(stage)}</span>
        <span className="t-label text-muted" title={`${cards.length} apps, ${money(spend)} monthly spend`}>
          {cards.length} · {money(spend)}
        </span>
      </header>
      <ul className="flex flex-1 flex-col gap-3 p-3">{children}</ul>
    </section>
  );
}

export default function Pipeline() {
  const f = useUrlFilters();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const toast = useToast();
  const apply = useApplyAppEvent();
  const { readOnly } = useSession();
  const [announcement, announce] = useAnnouncer();
  const [dragId, setDragId] = useState<string | null>(null);
  const [moveMode, setMoveMode] = useState<{ appId: string; target: number } | null>(null);
  const [reasonFor, setReasonFor] = useState<{ card: BoardCard; to: Stage; source: Source } | null>(null);
  const [conflict, setConflict] = useState<Conflict | null>(null);
  const [mobileStage, setMobileStage] = useState<Stage>((f.get("stage") as Stage) || "review_gates");
  const boardRef = useRef<HTMLDivElement>(null);
  const scrollSpeed = useRef(0);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

  const params = { platform: f.platform, owner: f.get("owner"), include_moves: "true" };
  const key = ["apps", "pipeline", params];
  const cards = useQuery({ queryKey: key, queryFn: () => api.get<BoardCard[]>(`/apps${query(params)}`), refetchInterval: 60_000 });
  const stageFilter = f.get("stage", "all");

  const focusCard = (id: string) => requestAnimationFrame(() => document.querySelector<HTMLElement>(`[data-app="${id}"]`)?.focus());

  const mutation = useMutation({
    mutationFn: (v: { card: BoardCard; to: Stage; reason?: string; source: Source; version?: number }) =>
      api.post<{ app: AppCard & { version: number }; event: AppEvent }>(`/apps/${v.card.app_id}/move`, {
        to_stage: v.to,
        expected_version: v.version ?? v.card.version,
        reason: v.reason,
        source: v.source,
      }),
    onMutate: async (v) => {
      await qc.cancelQueries({ queryKey: key });
      const previous = qc.getQueryData<BoardCard[]>(key);
      qc.setQueryData<BoardCard[]>(key, (old) => old?.map((c) => (c.app_id === v.card.app_id ? { ...c, stage: v.to } : c)));
      return { previous };
    },
    onError: (err, v, context) => {
      qc.setQueryData(key, context?.previous);
      track("app_stage_change_failed", "pipeline", v.card.app_id);
      if (err instanceof ApiError && err.status === 409) {
        setConflict({ ...v, current: err.body.current as Conflict["current"] });
        announce(`${v.card.name} changed since you loaded it. Choose the server version or retry.`);
      } else {
        toast({ kind: "error", message: `${v.card.name} stayed in ${label(v.card.stage)}: ${err.message}` });
        announce(`Move failed: ${err.message}`);
      }
      focusCard(v.card.app_id);
    },
    onSuccess: (res, v) => {
      track("app_stage_change_completed", "pipeline", v.card.app_id);
      apply({ app_id: v.card.app_id, stage: res.app.stage as Stage, version: res.app.version }, res.event);
      announce(`${v.card.name} moved to ${label(v.to)}.`);
      toast({
        kind: "undo",
        message: `${v.card.name} moved to ${label(v.to)}`,
        onUndo: () =>
          void api
            .post(`/apps/${v.card.app_id}/undo`, { event_id: res.event.event_id, expected_version: res.app.version })
            .then(() => {
              apply({ app_id: v.card.app_id });
              announce(`Move undone. ${v.card.name} is back in ${label(v.card.stage)}.`);
            })
            .catch((e: Error) => toast({ kind: "error", message: `Undo failed: ${e.message}` })),
      });
      focusCard(v.card.app_id);
    },
  });

  /** Validate locally first so a missing requirement is announced before any mutation. */
  const attempt = useCallback(
    (card: BoardCard, to: Stage, source: Source) => {
      if (to === card.stage) return;
      const move = card.moves?.[to];
      if (!move) {
        const msg = `${card.name} cannot move from ${label(card.stage)} to ${label(to)}.`;
        announce(msg);
        toast({ kind: "warning", message: msg });
        focusCard(card.app_id);
        return;
      }
      if (!move.allowed && move.code !== "reason") {
        const msg = `Blocked: ${label(to)} requires ${move.message?.replace(/^A |^An /, "a ").toLowerCase() ?? "more evidence"}.`;
        announce(msg);
        toast({ kind: "warning", message: msg });
        track("app_stage_change_failed", "pipeline", card.app_id);
        focusCard(card.app_id);
        return;
      }
      if (move.needs_reason) {
        setReasonFor({ card, to, source });
        return;
      }
      mutation.mutate({ card, to, source });
    },
    [announce, mutation, toast],
  );

  // Auto-scroll within 48 px of the board edges, up to 24 px per frame.
  useEffect(() => {
    if (!dragId) return;
    let frame = 0;
    const tick = () => {
      if (boardRef.current && scrollSpeed.current) boardRef.current.scrollLeft += scrollSpeed.current;
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [dragId]);

  const onDragMove = (e: DragMoveEvent) => {
    const rect = boardRef.current?.getBoundingClientRect();
    const start = (e.activatorEvent as PointerEvent).clientX;
    if (!rect || start === undefined) return;
    const x = start + e.delta.x;
    if (x < rect.left + EDGE) scrollSpeed.current = -MAX_SPEED * Math.min(1, (rect.left + EDGE - x) / EDGE);
    else if (x > rect.right - EDGE) scrollSpeed.current = MAX_SPEED * Math.min(1, (x - (rect.right - EDGE)) / EDGE);
    else scrollSpeed.current = 0;
  };
  const onDragStart = (e: DragStartEvent) => {
    setDragId(String(e.active.id));
    track("app_drag_started", "pipeline", String(e.active.id));
  };
  const onDragEnd = (e: DragEndEvent) => {
    scrollSpeed.current = 0;
    setDragId(null);
    const card = cards.data?.find((c) => c.app_id === e.active.id);
    if (card && e.over) attempt(card, e.over.id as Stage, "drag");
  };

  const onKey = (e: React.KeyboardEvent, c: BoardCard) => {
    if (readOnly) return;
    const idx = STAGES.indexOf(c.stage);
    if (!moveMode || moveMode.appId !== c.app_id) {
      if (e.key === " ") {
        e.preventDefault();
        setMoveMode({ appId: c.app_id, target: idx });
        announce(`Move mode for ${c.name}. Use Left and Right to choose a stage, Enter to confirm, Escape to cancel.`);
      }
      return;
    }
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      const next = Math.max(0, Math.min(STAGES.length - 1, moveMode.target + (e.key === "ArrowRight" ? 1 : -1)));
      setMoveMode({ ...moveMode, target: next });
      const stage = STAGES[next]!;
      const m = c.moves?.[stage];
      announce(`${label(stage)}${stage === c.stage ? ", current stage" : m?.allowed ? ", allowed" : m ? `, blocked: ${m.message}` : ", not allowed"}`);
    } else if (e.key === "Enter") {
      e.preventDefault();
      const to = STAGES[moveMode.target]!;
      setMoveMode(null);
      attempt(c, to, "keyboard");
    } else if (e.key === "Escape") {
      e.preventDefault();
      setMoveMode(null);
      announce("Move cancelled.");
    }
  };

  const onMenu = (c: BoardCard, action: "open" | "edit" | "move" | "archive") => {
    if (action === "open") f.set({ app: c.app_id });
    else if (action === "edit") navigate(`/apps/${c.app_id}`);
    else if (action === "move") {
      setMoveMode({ appId: c.app_id, target: STAGES.indexOf(c.stage) });
      focusCard(c.app_id);
      announce(`Move mode for ${c.name}. Use Left and Right to choose a stage, Enter to confirm.`);
    } else attempt(c, "retired", "menu");
  };

  const dragging = cards.data?.find((c) => c.app_id === dragId) ?? null;
  const moving = cards.data?.find((c) => c.app_id === moveMode?.appId) ?? null;
  const visibleStages = stageFilter === "all" ? STAGES : STAGES.filter((s) => s === stageFilter);
  const narrow = typeof window !== "undefined" && window.innerWidth < 720;

  return (
    <>
      <HeaderBand page="pipeline" title="Pipeline" summary="Every app by lifecycle stage. Drag a card, or focus it and press Space, to move it; the server checks every move against the lifecycle rules and your role.">
        <div className="no-print flex flex-wrap gap-2">
          <Select label="Stage filter" value={stageFilter} onChange={(v) => f.set({ stage: v === "all" ? null : v })} options={[{ value: "all", label: "All stages" }, ...STAGES.map((s) => ({ value: s, label: label(s) }))]} />
          <ProvenanceBadge label="SYNTHETIC" />
        </div>
      </HeaderBand>
      <p id="pipeline-help" className="sr-only">
        Press Space to start moving this card, Left and Right arrows to choose a stage, Enter to confirm, Escape to cancel.
      </p>
      <div aria-live="assertive" role="status" className="sr-only" data-testid="announcer">
        {announcement}
      </div>

      {cards.isLoading ? (
        <div className="flex gap-4 overflow-hidden">
          {STAGES.slice(0, 5).map((s) => (
            <Skeleton key={s} className="h-96 w-[280px] shrink-0" />
          ))}
        </div>
      ) : cards.error ? (
        <ModuleError error={cards.error} onRetry={() => void cards.refetch()} />
      ) : cards.data?.length === 0 ? (
        <EmptyState illustration="no-apps" title="No apps registered" missing="The registry is empty." action={<span className="t-label text-muted">Run cp importregistry with a CSV export.</span>} />
      ) : narrow ? (
        <section aria-label="Pipeline, one stage at a time" className="flex flex-col gap-3">
          <Select label="Stage" value={mobileStage} onChange={(v) => setMobileStage(v as Stage)} options={STAGES.map((s) => ({ value: s, label: `${label(s)} (${cards.data?.filter((c) => c.stage === s).length ?? 0})` }))} />
          <ul className="flex flex-col gap-3">
            {cards.data
              ?.filter((c) => c.stage === mobileStage)
              .map((c) => (
                <li key={c.app_id} data-app={c.app_id} tabIndex={0} className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-4">
                  <CardBody c={c} />
                  {!readOnly && (
                    <Select
                      label={`Move ${c.name}`}
                      value=""
                      onChange={(v) => v && attempt(c, v as Stage, "menu")}
                      options={[{ value: "", label: "Move to…" }, ...STAGES.filter((s) => s !== c.stage && c.moves?.[s]).map((s) => ({ value: s, label: label(s) }))]}
                    />
                  )}
                </li>
              ))}
          </ul>
        </section>
      ) : (
        <DndContext sensors={sensors} onDragStart={onDragStart} onDragMove={onDragMove} onDragEnd={onDragEnd} onDragCancel={() => setDragId(null)} autoScroll={false}>
          <div ref={boardRef} className="flex gap-4 relative overflow-x-auto pb-4" data-testid="board">
            {visibleStages.map((stage, i) => {
              const inStage = cards.data?.filter((c) => c.stage === stage) ?? [];
              const valid = !!dragging && dragging.stage !== stage && !!dragging.moves?.[stage]?.allowed;
              const target = !!moving && moveMode?.target === STAGES.indexOf(stage) && moving.stage !== stage;
              return (
                <Column key={stage} stage={stage} cards={inStage} valid={valid} target={target}>
                  {inStage.map((c) => (
                    <BoardCardView key={c.app_id} c={c} moving={moveMode?.appId === c.app_id} onKey={onKey} onMenu={onMenu} disabled={readOnly || !c.moves || Object.keys(c.moves).length === 0} />
                  ))}
                  {inStage.length === 0 && <li className="t-label p-2 text-center font-normal text-muted">{i === 0 ? "No new apps" : "Empty"}</li>}
                </Column>
              );
            })}
          </div>
          <DragOverlay>
            {dragging && (
              <div className="flex min-h-36 w-[256px] scale-[0.96] flex-col gap-3 rounded-xl border border-accent bg-surface p-4" style={{ boxShadow: "0 12px 24px rgb(0 0 0 / 0.35)" }}>
                <CardBody c={dragging} />
              </div>
            )}
          </DragOverlay>
        </DndContext>
      )}

      <ReasonDialog
        pending={reasonFor}
        onCancel={() => {
          if (reasonFor) focusCard(reasonFor.card.app_id);
          setReasonFor(null);
        }}
        onConfirm={(reason) => {
          if (!reasonFor) return;
          mutation.mutate({ ...reasonFor, reason });
          setReasonFor(null);
        }}
      />
      <ConflictDrawer
        conflict={conflict}
        onUseServer={() => {
          if (!conflict) return;
          apply({ app_id: conflict.card.app_id, stage: conflict.current.stage, version: conflict.current.version });
          focusCard(conflict.card.app_id);
          setConflict(null);
        }}
        onRetry={() => {
          if (!conflict) return;
          mutation.mutate({ card: conflict.card, to: conflict.to, reason: conflict.reason, source: conflict.source, version: conflict.current.version });
          setConflict(null);
        }}
        onClose={() => setConflict(null)}
      />
      <AppDrawer appId={f.get("app") || null} onClose={() => f.set({ app: null })} />
    </>
  );
}

function ReasonDialog({ pending, onCancel, onConfirm }: { pending: { card: BoardCard; to: Stage } | null; onCancel: () => void; onConfirm: (reason: string) => void }) {
  const [reason, setReason] = useState("");
  useEffect(() => setReason(""), [pending]);
  return (
    <Drawer open={!!pending} onClose={onCancel} width={420} dirty={reason.length > 0} title={pending ? `Move ${pending.card.name} to ${label(pending.to)}` : "Move"}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (reason.trim()) onConfirm(reason.trim());
        }}
        className="flex flex-col gap-3"
      >
        <label className="t-label flex flex-col gap-1 text-muted">
          Reason (required, recorded in the audit trail)
          <Input autoFocus value={reason} onChange={(e) => setReason(e.target.value)} />
        </label>
        <div className="flex gap-2">
          <Button type="submit" variant="primary" disabled={!reason.trim()}>
            Move
          </Button>
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </form>
    </Drawer>
  );
}

function ConflictDrawer({ conflict, onUseServer, onRetry, onClose }: { conflict: Conflict | null; onUseServer: () => void; onRetry: () => void; onClose: () => void }) {
  return (
    <Drawer open={!!conflict} onClose={onClose} width={420} title="This app changed since you loaded it">
      {conflict && (
        <div className="flex flex-col gap-4" data-testid="conflict-drawer">
          <p className="t-body">
            Someone else updated <strong>{conflict.card.name}</strong> before your move reached the server. Nothing was changed by your move.
          </p>
          <dl className="t-body grid grid-cols-2 gap-2 rounded-lg border border-line p-3">
            <dt className="text-muted">Your view</dt>
            <dd>
              {label(conflict.card.stage)} (version {conflict.card.version})
            </dd>
            <dt className="text-muted">Server now</dt>
            <dd>
              {label(conflict.current.stage)} (version {conflict.current.version})
            </dd>
            <dt className="text-muted">You tried</dt>
            <dd>Move to {label(conflict.to)}</dd>
          </dl>
          <div className="flex flex-wrap gap-2">
            <Button variant="primary" onClick={onUseServer}>
              Use server version
            </Button>
            <Button onClick={onRetry}>Review and retry</Button>
          </div>
        </div>
      )}
    </Drawer>
  );
}
