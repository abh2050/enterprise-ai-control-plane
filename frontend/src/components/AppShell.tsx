import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router";
import { get, getFixtureUser, label, setFixtureUser, type Me, type ModeInfo } from "../api";
import { ProvenanceBadge } from "./ui";

const NAV = [
  { to: "/", label: "Portfolio" },
  { to: "/pipeline", label: "Pipeline" },
  { to: "/flow", label: "Flow" },
  { to: "/apps/support-triage", label: "Support Triage" },
  { to: "/reviews", label: "Reviews" },
  { to: "/incidents", label: "Incidents" },
];

const MODE_TEXT: Record<ModeInfo["data_mode"], string> = {
  LIVE: "Live data from this deployment.",
  SIMULATED: "Simulated traffic. Numbers come from replayed data, not production.",
  FIXTURE: "Fixture data. Numbers are placeholders for local development and demos.",
};

export function DataModeBanner() {
  const { data } = useQuery({ queryKey: ["mode"], queryFn: () => get<ModeInfo>("/mode") });
  if (!data) return null;
  const tone =
    data.data_mode === "LIVE" ? "bg-ok-bg text-ok" : "bg-warn-bg text-warn";
  return (
    <div role="status" className={`px-4 py-1.5 text-xs ${tone}`}>
      <div className="mx-auto flex max-w-screen-2xl flex-wrap items-center gap-x-3 gap-y-1">
        <span className="font-semibold tracking-wide">DATA MODE: {data.data_mode}</span>
        <span>{MODE_TEXT[data.data_mode]}</span>
        {data.dataset_labels.map((l) => (
          <ProvenanceBadge key={l} label={l} />
        ))}
      </div>
    </div>
  );
}

function IdentitySwitcher() {
  const qc = useQueryClient();
  const mode = useQuery({ queryKey: ["mode"], queryFn: () => get<ModeInfo>("/mode") });
  const fixture = mode.data?.identity_mode === "fixture";
  const users = useQuery({
    queryKey: ["fixture-users"],
    queryFn: () => get<Me[]>("/fixture/users"),
    enabled: fixture,
  });
  const me = useQuery({ queryKey: ["me"], queryFn: () => get<Me>("/me"), retry: false });
  const [current, setCurrent] = useState(getFixtureUser() ?? "");

  if (!fixture) {
    return <span className="text-xs text-muted">{me.data ? me.data.email : "Signed out"}</span>;
  }
  return (
    <label className="flex items-center gap-2 text-xs text-muted">
      <span className="hidden sm:inline">Fixture identity</span>
      <select
        className="rounded border border-line bg-surface px-2 py-1 text-ink"
        value={current}
        onChange={(e) => {
          setCurrent(e.target.value);
          setFixtureUser(e.target.value || null);
          void qc.invalidateQueries();
        }}
      >
        <option value="">Choose…</option>
        {users.data?.map((u) => (
          <option key={u.email} value={u.email}>
            {u.email} ({label(u.role)})
          </option>
        ))}
      </select>
    </label>
  );
}

type Theme = "system" | "light" | "dark";

function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      return (localStorage.getItem("cp.theme") as Theme | null) ?? "system";
    } catch {
      return "system";
    }
  });
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("cp.theme", theme);
    } catch {
      // per-viewer convenience only
    }
  }, [theme]);
  const next: Record<Theme, Theme> = { system: "light", light: "dark", dark: "system" };
  return (
    <button
      type="button"
      className="rounded border border-line px-2 py-1 text-xs text-muted hover:text-ink"
      onClick={() => setTheme(next[theme])}
      aria-label={`Theme: ${theme}. Switch to ${next[theme]}.`}
    >
      Theme: {label(theme)}
    </button>
  );
}

export function AppShell() {
  return (
    <div className="min-h-screen">
      <DataModeBanner />
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-screen-2xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <span className="text-sm font-semibold">AI Control Plane</span>
          <nav aria-label="Main" className="order-3 -mx-1 flex w-full gap-1 overflow-x-auto md:order-none md:w-auto">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded px-2.5 py-1.5 text-sm ${
                    isActive ? "bg-accent text-accent-contrast" : "text-muted hover:text-ink"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <IdentitySwitcher />
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-screen-2xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
