// App shell (console spec Section 9A): sidebar, sticky top bar, data mode banner.
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AppWindow,
  Briefcase,
  ChevronDown,
  ClipboardCheck,
  GitBranch,
  LayoutGrid,
  Moon,
  Search,
  Settings,
  Siren,
  Sun,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { NavLink, Outlet, useNavigate } from "react-router";
import { api, getFixtureUser, PLATFORMS, query, setFixtureUser, SNAPSHOT, type AppCard, type Me, type ModeInfo } from "../lib/api";
import { label } from "../lib/format";
import { useTheme, useUrlFilters } from "../lib/state";
import { cx, IconButton, ProvenanceBadge, Select } from "./ui";

interface Session {
  me: Me | null;
  can: (permission: string) => boolean;
  readOnly: boolean;
}
const SessionContext = createContext<Session>({ me: null, can: () => false, readOnly: true });
export const useSession = () => useContext(SessionContext);

const NAV: { to: string; label: string; icon: LucideIcon; permission: string }[] = [
  { to: "/portfolio", label: "Portfolio", icon: LayoutGrid, permission: "read_portfolio" },
  { to: "/pipeline", label: "Pipeline", icon: Workflow, permission: "read_app_detail" },
  { to: "/flow", label: "Flow", icon: GitBranch, permission: "read_flow" },
  { to: "/apps", label: "Applications", icon: AppWindow, permission: "read_app_detail" },
  { to: "/reviews", label: "Reviews", icon: ClipboardCheck, permission: "read_reviews" },
  { to: "/incidents", label: "Incidents", icon: Siren, permission: "read_incidents" },
  { to: "/settings", label: "Settings", icon: Settings, permission: "read_portfolio" },
];

const MODE_TEXT: Record<ModeInfo["data_mode"], string> = {
  LIVE: "Live data from this deployment.",
  SIMULATED: "Simulated traffic. Numbers come from replayed data, not production.",
  FIXTURE: "Fixture mode. Local identities and sample data; measured results come from real runs.",
};

function DataModeBanner({ mode }: { mode: ModeInfo | undefined }) {
  if (!mode) return <div className="h-9" />;
  const live = mode.data_mode === "LIVE";
  return (
    <div role="status" className={cx("t-label flex min-h-9 flex-wrap items-center gap-x-3 gap-y-1 border-b border-line px-8 py-2", live ? "text-healthy" : "text-warning")}>
      <span className="tracking-wide">DATA MODE: {mode.data_mode}</span>
      <span className="font-normal text-muted">{MODE_TEXT[mode.data_mode]}</span>
      {mode.dataset_labels.includes("SYNTHETIC") && (
        <span className="inline-flex items-center gap-2">
          <ProvenanceBadge label="SYNTHETIC" />
          <span className="font-normal text-muted">The registry is a generated sample organization, not real data.</span>
        </span>
      )}
      {SNAPSHOT && (
        <span className="inline-flex items-center gap-2 text-info">
          SNAPSHOT <span className="font-normal text-muted">Static export with no backend. Every write control is disabled.</span>
        </span>
      )}
    </div>
  );
}

function GlobalSearch() {
  const ref = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const results = useQuery({
    queryKey: ["apps", "search", q],
    queryFn: () => api.get<AppCard[]>(`/apps${query({ q, sort: "name" })}`),
    enabled: q.trim().length > 1,
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) {
        e.preventDefault();
        ref.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return (
    <div className="relative min-w-0 flex-1 max-w-md">
      <Search size={16} strokeWidth={1.75} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted" aria-hidden />
      <input
        ref={ref}
        type="search"
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
        placeholder="Search apps, owners, problems"
        aria-label="Search applications (press / to focus)"
        aria-keyshortcuts="/"
        className="m-hover h-9 w-full rounded-lg border border-line-strong bg-surface pr-10 pl-9 text-ink placeholder:text-muted"
      />
      <kbd className="t-label pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 rounded border border-line px-1 text-muted">/</kbd>
      {open && q.trim().length > 1 && (
        <ul className="shadow-overlay absolute top-11 left-0 z-30 max-h-80 w-full overflow-auto rounded-xl border border-line bg-overlay p-2" role="listbox" aria-label="Search results">
          {(results.data ?? []).slice(0, 8).map((a) => (
            <li key={a.app_id}>
              <button
                type="button"
                className="m-hover flex w-full flex-col rounded-lg px-3 py-2 text-left hover:bg-raised"
                onMouseDown={() => {
                  navigate(`/apps?app=${a.app_id}`);
                  setQ("");
                }}
              >
                <span className="t-card">{a.name}</span>
                <span className="t-label text-muted">
                  {a.owner ?? "No owner"} · {label(a.stage)}
                </span>
              </button>
            </li>
          ))}
          {results.data?.length === 0 && <li className="t-body px-3 py-2 text-muted">No matching apps</li>}
        </ul>
      )}
    </div>
  );
}

function AvatarMenu({ me, mode }: { me: Me | null; mode: ModeInfo | undefined }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const fixture = mode?.identity_mode === "fixture" && !SNAPSHOT;
  const users = useQuery({ queryKey: ["fixture-users"], queryFn: () => api.get<{ email: string; role: string }[]>("/fixture/users"), enabled: fixture });
  const initials = me ? me.email.slice(0, 2).toUpperCase() : "?";
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={me ? `Signed in as ${me.email}, ${label(me.role)}` : "Choose an identity"}
        title={me ? `${me.email} (${label(me.role)})` : "Choose an identity"}
        className="m-hover flex h-9 items-center gap-2 rounded-lg px-2 hover:bg-raised"
      >
        <span className="t-label flex size-7 items-center justify-center rounded-full bg-accent-soft text-accent">{initials}</span>
        <ChevronDown size={16} strokeWidth={1.75} aria-hidden />
      </button>
      {open && (
        <div role="menu" className="shadow-overlay absolute top-11 right-0 z-30 w-72 rounded-xl border border-line bg-overlay p-2">
          <div className="t-label px-3 py-2 text-muted">{me ? `${me.email} · ${label(me.role)}` : "Not signed in"}</div>
          {fixture &&
            users.data?.map((u) => (
              <button
                key={u.email}
                role="menuitemradio"
                aria-checked={me?.email === u.email}
                type="button"
                className={cx("m-hover flex w-full items-center justify-between rounded-lg px-3 py-2 text-left hover:bg-raised", me?.email === u.email && "bg-accent-soft")}
                onClick={() => {
                  setFixtureUser(u.email);
                  setOpen(false);
                  void qc.invalidateQueries();
                }}
              >
                <span className="t-body">{u.email}</span>
                <span className="t-label text-muted">{label(u.role)}</span>
              </button>
            ))}
        </div>
      )}
    </div>
  );
}

function TopBar({ me, mode, theme, setTheme }: { me: Me | null; mode: ModeInfo | undefined; theme: string; setTheme: (t: "dark" | "light") => void }) {
  const f = useUrlFilters();
  return (
    <header className="no-print sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-line bg-canvas/95 px-4 backdrop-blur min-[1024px]:px-8">
      <GlobalSearch />
      <div className="ml-auto flex items-center gap-2">
        {mode && (
          <span className={cx("t-label hidden rounded-full border px-3 py-1 min-[720px]:inline", mode.data_mode === "LIVE" ? "border-healthy text-healthy" : "border-warning text-warning")} title="Data mode">
            {mode.data_mode}
          </span>
        )}
        <Select
          label="Date range"
          value={String(f.range)}
          onChange={(v) => f.set({ range: v === "90" ? null : v })}
          options={[
            { value: "30", label: "Last 30 days" },
            { value: "90", label: "Last 90 days" },
            { value: "180", label: "Last 180 days" },
          ]}
          className="hidden min-[720px]:block"
        />
        <Select
          label="Platform"
          value={f.platform}
          onChange={(v) => f.set({ platform: v || null })}
          options={[{ value: "", label: "All platforms" }, ...PLATFORMS.map((p) => ({ value: p, label: label(p) }))]}
        />
        <IconButton icon={theme === "dark" ? Sun : Moon} label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"} onClick={() => setTheme(theme === "dark" ? "light" : "dark")} />
        <AvatarMenu me={me} mode={mode} />
      </div>
    </header>
  );
}

function Sidebar({ items }: { items: typeof NAV }) {
  return (
    <>
      <nav aria-label="Main" className="no-print sticky top-0 hidden h-screen shrink-0 flex-col gap-1 border-r border-line bg-surface p-6 min-[1024px]:flex min-[1024px]:w-20 min-[1024px]:px-4 min-[1280px]:w-60 min-[1280px]:px-6">
        <div className="mb-6 flex items-center gap-2 px-2">
          <Briefcase size={20} strokeWidth={1.75} className="text-accent" aria-hidden />
          <span className="t-card hidden min-[1280px]:inline">AI Control Plane</span>
        </div>
        {items.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            title={n.label}
            className={({ isActive }) =>
              cx("m-hover flex h-11 items-center gap-3 rounded-lg px-3 t-card", isActive ? "bg-accent-soft text-accent" : "text-muted hover:bg-raised hover:text-ink")
            }
          >
            <n.icon size={20} strokeWidth={1.75} aria-hidden />
            <span className="hidden min-[1280px]:inline">{n.label}</span>
            <span className="sr-only min-[1280px]:hidden">{n.label}</span>
          </NavLink>
        ))}
      </nav>
      <nav aria-label="Main" className="no-print fixed inset-x-0 bottom-0 z-30 flex h-14 items-stretch justify-around border-t border-line bg-surface min-[1024px]:hidden">
        {items.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            title={n.label}
            aria-label={n.label}
            className={({ isActive }) => cx("flex min-w-11 flex-1 items-center justify-center", isActive ? "text-accent" : "text-muted")}
          >
            <n.icon size={20} strokeWidth={1.75} aria-hidden />
          </NavLink>
        ))}
      </nav>
    </>
  );
}

export function Shell({ children }: { children?: ReactNode }) {
  const mode = useQuery({ queryKey: ["mode"], queryFn: () => api.get<ModeInfo>("/mode"), staleTime: Infinity });
  const me = useQuery({ queryKey: ["me", getFixtureUser()], queryFn: () => api.get<Me>("/me"), retry: false, staleTime: Infinity });
  const user = me.data ?? null;
  const [theme, setTheme] = useTheme(user?.email ?? null);
  const can = (p: string) => !!user?.permissions.includes(p);
  const readOnly = SNAPSHOT || !user || user.role === "executive_viewer";
  const items = NAV.filter((n) => !user || can(n.permission));
  return (
    <SessionContext.Provider value={{ me: user, can, readOnly }}>
      <div className="flex min-h-screen">
        <Sidebar items={items} />
        <div className="flex min-w-0 flex-1 flex-col pb-14 min-[1024px]:pb-0">
          <TopBar me={user} mode={mode.data} theme={theme} setTheme={setTheme} />
          <DataModeBanner mode={mode.data} />
          <main className="mx-auto w-full max-w-[1600px] px-4 py-7 min-[720px]:px-8">{children ?? <Outlet />}</main>
        </div>
      </div>
    </SessionContext.Provider>
  );
}
