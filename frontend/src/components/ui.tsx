// Design system components (console spec Section 9A). Every component implements the
// states the spec lists. Status always pairs color with an icon and a text label.
import {
  AlertTriangle,
  CheckCircle2,
  Info,
  Loader2,
  OctagonAlert,
  RefreshCw,
  Table2,
  X,
  type LucideIcon,
} from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type TextareaHTMLAttributes,
} from "react";
import type { DatasetLabel, Health, Metric, Provenance } from "../lib/api";
import { now as clockNow } from "../lib/clock";
import { exactMetric, metricText, relative, timestamp } from "../lib/format";

const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

// Buttons: default, hover, focus, active, disabled, loading

type Variant = "primary" | "secondary" | "ghost" | "danger";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-on-accent hover:bg-accent-strong active:bg-accent-strong",
  secondary: "border border-line-strong bg-surface text-ink hover:bg-raised active:bg-raised",
  ghost: "text-ink hover:bg-raised active:bg-raised",
  danger: "border border-danger text-danger hover:bg-raised",
};

export function Button({
  variant = "secondary",
  loading = false,
  icon: Icon,
  children,
  className,
  disabled,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean; icon?: LucideIcon }) {
  return (
    <button
      type="button"
      {...rest}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cx(
        "m-hover inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 t-card disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-9",
        VARIANTS[variant],
        className,
      )}
    >
      {loading ? <Loader2 size={16} strokeWidth={1.75} className="animate-spin" aria-hidden /> : Icon && <Icon size={16} strokeWidth={1.75} aria-hidden />}
      {children}
    </button>
  );
}

/** Icon-only control: always has a tooltip and an accessible name. */
export function IconButton({
  icon: Icon,
  label,
  className,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { icon: LucideIcon; label: string }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      {...rest}
      className={cx("m-hover inline-flex size-11 items-center justify-center rounded-lg text-muted hover:bg-raised hover:text-ink disabled:opacity-50 sm:size-9", className)}
    >
      <Icon size={20} strokeWidth={1.75} aria-hidden />
    </button>
  );
}

// Inputs: empty, value, focus, error, disabled

export function Field({
  label,
  error,
  hint,
  children,
  id,
}: {
  label: string;
  error?: string | null;
  hint?: string;
  children: (props: { id: string; "aria-invalid"?: boolean; "aria-describedby"?: string }) => ReactNode;
  id?: string;
}) {
  const auto = useId();
  const fid = id ?? auto;
  const describe = error ? `${fid}-error` : hint ? `${fid}-hint` : undefined;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={fid} className="t-label text-muted">
        {label}
      </label>
      {children({ id: fid, "aria-invalid": error ? true : undefined, "aria-describedby": describe })}
      {error ? (
        <span id={`${fid}-error`} className="t-label flex items-center gap-1 text-danger">
          <OctagonAlert size={16} strokeWidth={1.75} aria-hidden /> {error}
        </span>
      ) : hint ? (
        <span id={`${fid}-hint`} className="t-label text-muted">
          {hint}
        </span>
      ) : null}
    </div>
  );
}

const control =
  "m-hover min-h-11 rounded-lg border border-line-strong bg-surface px-3 text-ink placeholder:text-muted disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-danger sm:min-h-9";

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cx(control, props.className)} />;
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cx(control, "py-2", props.className)} />;
}

export function Select({
  value,
  onChange,
  options,
  label,
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  label: string;
  className?: string;
}) {
  return (
    <select aria-label={label} title={label} value={value} onChange={(e) => onChange(e.target.value)} className={cx(control, className)}>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

// Provenance and status

const BADGE: Record<Provenance | DatasetLabel, { cls: string; help: string }> = {
  MEASURED: { cls: "border-healthy text-healthy", help: "Measured from real runs of this system" },
  SIMULATED: { cls: "border-info text-info", help: "Computed from simulated traffic" },
  FIXTURE: { cls: "border-warning text-warning", help: "Sample data for demos and local development" },
  ASSUMPTION: { cls: "border-line-strong text-muted", help: "An assumed input, not a measurement" },
  SYNTHETIC: { cls: "border-warning text-warning", help: "Generated sample registry, not a real organization" },
  AUTHORED: { cls: "border-line-strong text-muted", help: "Written by one person; single rater" },
  IMPORTED: { cls: "border-info text-info", help: "Imported from an organization's CSV export" },
};

export function ProvenanceBadge({ label }: { label: Provenance | DatasetLabel }) {
  const b = BADGE[label] ?? BADGE.ASSUMPTION;
  return (
    <span title={b.help} className={cx("inline-flex h-5 items-center rounded-full border px-2 text-[10px] font-semibold tracking-wide", b.cls)}>
      {label}
      <span className="sr-only">: {b.help}</span>
    </span>
  );
}

const HEALTH: Record<Health, { icon: LucideIcon; text: string; cls: string }> = {
  healthy: { icon: CheckCircle2, text: "Healthy", cls: "text-healthy" },
  warning: { icon: AlertTriangle, text: "Warning", cls: "text-warning" },
  danger: { icon: OctagonAlert, text: "Danger", cls: "text-danger" },
};

export function HealthPill({ health, rule }: { health: Health; rule?: string }) {
  const h = HEALTH[health];
  return (
    <span title={rule ? `${h.text}: ${rule}` : h.text} className={cx("t-label inline-flex items-center gap-1", h.cls)}>
      <h.icon size={16} strokeWidth={1.75} aria-hidden />
      {h.text}
      {rule && <span className="sr-only">. Rule: {rule}</span>}
    </span>
  );
}

export function StatusText({ tone, icon: Icon, children }: { tone: "healthy" | "warning" | "danger" | "info"; icon: LucideIcon; children: ReactNode }) {
  const cls = { healthy: "text-healthy", warning: "text-warning", danger: "text-danger", info: "text-info" }[tone];
  return (
    <span className={cx("t-label inline-flex items-center gap-1", cls)}>
      <Icon size={16} strokeWidth={1.75} aria-hidden />
      {children}
    </span>
  );
}

// Cards and KPI cards: loading, value, zero, error, stale

export function Card({ children, className, title, action, updatedAt }: { children: ReactNode; className?: string; title?: ReactNode; action?: ReactNode; updatedAt?: string | null }) {
  return (
    <section
      tabIndex={updatedAt ? 0 : undefined}
      className={cx("group relative rounded-xl border border-line bg-surface p-6", className)}
    >
      {(title || action) && (
        <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
          {typeof title === "string" ? <h2 className="t-card">{title}</h2> : title}
          {action}
        </header>
      )}
      {children}
      {updatedAt && <Updated at={updatedAt} />}
    </section>
  );
}

/** "Updated {relative time}" on hover and focus; amber with a refresh after 5 minutes. */
export function Updated({ at, onRefresh }: { at: string; onRefresh?: () => void }) {
  const stale = clockNow() - new Date(at).getTime() > 5 * 60 * 1000;
  if (stale) {
    return (
      <span className="t-label mt-3 flex items-center gap-2 text-warning">
        <AlertTriangle size={16} strokeWidth={1.75} aria-hidden />
        <span title={timestamp(at)}>Data from {relative(at)}</span>
        {onRefresh && (
          <button type="button" onClick={onRefresh} className="underline">
            Refresh
          </button>
        )}
      </span>
    );
  }
  return (
    <span title={timestamp(at)} className="t-label pointer-events-none absolute right-4 bottom-2 text-muted opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 group-focus:opacity-100">
      Updated {relative(at)}
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("skeleton", className)} aria-hidden />;
}

export function KpiCard({
  title,
  metric,
  loading,
  error,
  onRetry,
  onClick,
  hint,
  updatedAt,
  extra,
}: {
  title: string;
  metric?: Metric;
  loading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  onClick?: () => void;
  hint?: string;
  updatedAt?: string | null;
  extra?: ReactNode;
}) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag
      type={onClick ? "button" : undefined}
      onClick={onClick}
      className={cx(
        "group relative flex h-28 w-full flex-col justify-between rounded-xl border border-line bg-surface p-5 text-left",
        onClick && "m-hover hover:border-accent",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="t-label text-muted">{title}</span>
        {metric && <ProvenanceBadge label={metric.provenance} />}
      </div>
      {loading ? (
        <Skeleton className="h-9 w-24" />
      ) : error ? (
        <ModuleError error={error} onRetry={onRetry} compact />
      ) : metric ? (
        <div className="flex items-end justify-between gap-2">
          <span className="t-kpi" aria-label={`${title}: ${exactMetric(metric.value, metric.unit)}`} title={`${exactMetric(metric.value, metric.unit)}. Source: ${metric.source}`}>
            {metricText(metric.value, metric.unit)}
          </span>
          <span className="t-label text-muted">{metric.value === 0 ? "None right now" : hint}</span>
        </div>
      ) : null}
      {extra}
      {updatedAt && !loading && !error && <Updated at={updatedAt} />}
    </Tag>
  );
}

export function MetricInline({ metric, title }: { metric: Metric; title?: string }) {
  return (
    <span className="inline-flex items-center gap-2" title={`${exactMetric(metric.value, metric.unit)}. Source: ${metric.source}`}>
      <span aria-label={title ? `${title}: ${exactMetric(metric.value, metric.unit)}` : exactMetric(metric.value, metric.unit)}>{metricText(metric.value, metric.unit)}</span>
      <ProvenanceBadge label={metric.provenance} />
    </span>
  );
}

// Errors and empty states

export function ModuleError({ error, onRetry, compact }: { error: Error; onRetry?: () => void; compact?: boolean }) {
  const status = (error as { status?: number }).status;
  const message =
    status === 401 ? "Choose an identity to load this." : status === 403 ? "Your role cannot view this module." : "This module failed to load.";
  return (
    <div role="alert" className={cx("flex items-center gap-3 text-muted", compact ? "t-label" : "t-body")}>
      <OctagonAlert size={16} strokeWidth={1.75} className="text-danger" aria-hidden />
      <span>{message}</span>
      {onRetry && status !== 403 && status !== 401 && (
        <Button variant="ghost" icon={RefreshCw} onClick={onRetry} className="min-h-8 px-2">
          Retry
        </Button>
      )}
    </div>
  );
}

const ILLUSTRATIONS = ["no-apps", "no-incidents", "no-reviews", "no-experiments", "no-shadow", "no-results", "stale", "onboarding"] as const;
export type Illustration = (typeof ILLUSTRATIONS)[number];

/** Empty state with a Section 9B illustration slot (placeholder poster until M8). */
export function EmptyState({ illustration, title, missing, action }: { illustration: Illustration; title: string; missing: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-4 rounded-xl border border-dashed border-line-strong bg-surface p-8 text-center">
      <div
        data-illustration={illustration}
        aria-hidden
        className="h-24 w-40 rounded-lg"
        style={{ background: "radial-gradient(circle at 30% 40%, var(--accent_soft), transparent 60%), linear-gradient(135deg, var(--hero_gradient_start), var(--hero_gradient_end))" }}
      />
      <div>
        <h3 className="t-card">{title}</h3>
        <p className="t-body mt-1 max-w-md text-muted">{missing}</p>
      </div>
      {action}
    </div>
  );
}

// Header band slot (Section 9B): placeholder poster until generated loops arrive in M8.

export function HeaderBand({ page, title, summary, variant = "default", children }: { page: string; title: string; summary: string; variant?: "default" | "incident"; children?: ReactNode }) {
  return (
    <div
      data-band={page}
      data-variant={variant}
      className="relative mb-6 flex min-h-40 items-end overflow-hidden rounded-xl border border-line p-6"
      style={{
        background:
          variant === "incident"
            ? "radial-gradient(ellipse at 75% 30%, color-mix(in srgb, var(--status_warning) 35%, transparent), transparent 60%), linear-gradient(120deg, var(--hero_gradient_start), var(--hero_gradient_end))"
            : "radial-gradient(ellipse at 78% 20%, color-mix(in srgb, var(--accent) 30%, transparent), transparent 55%), radial-gradient(ellipse at 95% 90%, color-mix(in srgb, var(--chart_2) 18%, transparent), transparent 50%), linear-gradient(120deg, var(--hero_gradient_start), var(--hero_gradient_end))",
      }}
    >
      {/* Scrim from bg_canvas at 70% keeps overlaid text at 4.5:1 over any imagery. */}
      <div className="absolute inset-y-0 left-0 w-2/3" style={{ background: "linear-gradient(90deg, color-mix(in srgb, var(--bg_canvas) 70%, transparent), transparent)" }} aria-hidden />
      <div className="relative flex w-full flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="t-page">{title}</h1>
          <p className="t-body mt-1 max-w-2xl text-muted">{summary}</p>
        </div>
        {children}
      </div>
    </div>
  );
}

// Charts: loading, data, empty, error, with a table alternative

export function ChartFrame({
  title,
  provenance,
  loading,
  error,
  empty,
  onRetry,
  table,
  hint,
  children,
  height,
}: {
  title: string;
  provenance: (Provenance | DatasetLabel)[];
  loading?: boolean;
  error?: Error | null;
  empty?: { title: string; missing: string } | null;
  onRetry?: () => void;
  table: ReactNode;
  hint?: string;
  children: ReactNode;
  height: number;
}) {
  const [showTable, setShowTable] = useState(false);
  return (
    <section className="flex h-full flex-col rounded-xl border border-line bg-surface p-6" aria-label={title}>
      <header className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="t-card">{title}</h2>
          {hint && <p className="t-label mt-1 text-muted">{hint}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {provenance.map((p) => (
            <ProvenanceBadge key={p} label={p} />
          ))}
          <IconButton icon={Table2} label={showTable ? "Show chart" : "Show as table"} aria-pressed={showTable} onClick={() => setShowTable((s) => !s)} />
        </div>
      </header>
      <div style={{ minHeight: height }} className="relative flex-1">
        {loading ? (
          <Skeleton className="absolute inset-0" />
        ) : error ? (
          <ModuleError error={error} onRetry={onRetry} />
        ) : empty ? (
          <EmptyState illustration="no-results" title={empty.title} missing={empty.missing} />
        ) : showTable ? (
          <div className="max-h-[420px] overflow-auto">{table}</div>
        ) : (
          children
        )}
      </div>
    </section>
  );
}

export function DataTable({ columns, rows, caption }: { columns: string[]; rows: ReactNode[][]; caption: string }) {
  return (
    <div className="max-w-full relative overflow-x-auto">
    <table className="w-full text-left t-body">
      <caption className="sr-only">{caption}</caption>
      <thead className="sticky top-0 bg-surface">
        <tr className="border-b border-line">
          {columns.map((c) => (
            <th key={c} scope="col" className="t-label py-2 pr-4 text-muted">
              {c}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className="border-b border-line last:border-0">
            {r.map((cell, j) => (
              <td key={j} className="py-2 pr-4">
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
    </div>
  );
}

export function Sparkline({ values, label }: { values: number[]; label: string }) {
  if (!values.length || values.every((v) => v === 0)) return <span className="t-label text-muted">No usage</span>;
  const max = Math.max(...values, 1);
  const pts = values.map((v, i) => `${(i / Math.max(1, values.length - 1)) * 80},${22 - (v / max) * 20}`).join(" ");
  return (
    <svg width="80" height="24" role="img" aria-label={`${label}: ${values.join(", ")} per week`}>
      <title>{`Weekly usage: ${values.map((v) => v.toLocaleString()).join(", ")}`}</title>
      <polyline points={pts} fill="none" stroke="var(--chart_1)" strokeWidth="1.75" />
    </svg>
  );
}

// Drawers: opening, open, dirty, saving, error

export function Drawer({
  open,
  onClose,
  title,
  width = 480,
  dirty,
  saving,
  error,
  footer,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  width?: 420 | 480;
  dirty?: boolean;
  saving?: boolean;
  error?: string | null;
  footer?: ReactNode;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const opener = useRef<Element | null>(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (open) {
      opener.current = document.activeElement;
      requestAnimationFrame(() => {
        setShown(true);
        ref.current?.focus();
      });
    } else {
      setShown(false);
      (opener.current as HTMLElement | null)?.focus?.();
    }
  }, [open]);
  const close = useCallback(() => {
    if (dirty && !window.confirm("Discard unsaved changes?")) return;
    onClose();
  }, [dirty, onClose]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, close]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40" role="presentation">
      <div className={cx("m-drawer absolute inset-0 bg-black/50", shown ? "opacity-100" : "opacity-0")} onClick={close} aria-hidden />
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === "string" ? title : "Details"}
        aria-busy={saving || undefined}
        tabIndex={-1}
        data-state={saving ? "saving" : error ? "error" : dirty ? "dirty" : shown ? "open" : "opening"}
        style={{ "--drawer-w": `${width}px` } as React.CSSProperties}
        className={cx(
          "m-drawer shadow-overlay absolute inset-y-0 right-0 flex w-full flex-col border-l border-line bg-overlay outline-none",
          "min-[720px]:w-[70vw] min-[1024px]:w-[var(--drawer-w)]",
          shown ? "translate-x-0" : "translate-x-full",
        )}
      >
        <header className="flex items-start justify-between gap-3 border-b border-line p-6">
          <div className="min-w-0 flex-1">{typeof title === "string" ? <h2 className="t-page truncate">{title}</h2> : title}</div>
          <IconButton icon={X} label="Close" onClick={close} />
        </header>
        {error && (
          <div role="alert" className="t-body flex items-center gap-2 border-b border-line px-6 py-3 text-danger">
            <OctagonAlert size={16} strokeWidth={1.75} aria-hidden /> {error}
          </div>
        )}
        <div className="flex-1 overflow-y-auto p-6">{children}</div>
        {footer && <footer className="border-t border-line p-4">{footer}</footer>}
      </div>
    </div>
  );
}

// Toasts: success, warning, error, undo

type ToastKind = "success" | "warning" | "error" | "undo";
interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
  onUndo?: () => void;
  expiresAt: number;
}
const ToastContext = createContext<(t: Omit<Toast, "id" | "expiresAt"> & { ms?: number }) => void>(() => undefined);
export const useToast = () => useContext(ToastContext);

const TOAST_ICON: Record<ToastKind, { icon: LucideIcon; cls: string }> = {
  success: { icon: CheckCircle2, cls: "text-healthy" },
  warning: { icon: AlertTriangle, cls: "text-warning" },
  error: { icon: OctagonAlert, cls: "text-danger" },
  undo: { icon: Info, cls: "text-info" },
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counter = useRef(0);
  const push = useCallback((t: Omit<Toast, "id" | "expiresAt"> & { ms?: number }) => {
    const id = ++counter.current;
    const ms = t.ms ?? (t.kind === "undo" ? 10_000 : 6_000);
    setToasts((all) => [...all, { ...t, id, expiresAt: Date.now() + ms }]);
    window.setTimeout(() => setToasts((all) => all.filter((x) => x.id !== id)), ms);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="no-print pointer-events-none fixed right-4 bottom-20 z-50 flex w-[min(420px,calc(100vw-32px))] flex-col gap-2 min-[1024px]:bottom-4" aria-live="polite" role="status">
        {toasts.map((t) => {
          const ic = TOAST_ICON[t.kind];
          return (
            <div key={t.id} data-kind={t.kind} className="shadow-overlay pointer-events-auto flex items-center gap-3 rounded-xl border border-line bg-overlay p-4">
              <ic.icon size={16} strokeWidth={1.75} className={ic.cls} aria-hidden />
              <span className="t-body flex-1">{t.message}</span>
              {t.onUndo && (
                <Button
                  variant="ghost"
                  className="min-h-8 px-2"
                  onClick={() => {
                    t.onUndo?.();
                    setToasts((all) => all.filter((x) => x.id !== t.id));
                  }}
                >
                  Undo
                </Button>
              )}
              <IconButton icon={X} label="Dismiss" className="size-8" onClick={() => setToasts((all) => all.filter((x) => x.id !== t.id))} />
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

/** Polite live region for keyboard moves and other announcements. */
export function useAnnouncer(): [string, (m: string) => void] {
  const [msg, setMsg] = useState("");
  const announce = useCallback((m: string) => {
    setMsg("");
    requestAnimationFrame(() => setMsg(m));
  }, []);
  return [msg, announce];
}

export { cx };
