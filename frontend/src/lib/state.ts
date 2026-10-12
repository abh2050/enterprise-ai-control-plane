// URL filter state, analytics events, theme preference, and the shared event reducer.
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { api, SNAPSHOT, type AppCard, type AppEvent } from "./api";

/** Every filter lives in the URL so reloads, links, and drawers keep list state. */
export function useUrlFilters() {
  const [params, setParams] = useSearchParams();
  const get = useCallback((key: string, fallback = "") => params.get(key) ?? fallback, [params]);
  const set = useCallback(
    (updates: Record<string, string | null>) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [k, v] of Object.entries(updates)) {
            if (v === null || v === "") next.delete(k);
            else next.set(k, v);
          }
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );
  return {
    params,
    get,
    set,
    platform: get("platform"),
    range: Number(get("range", "90")) || 90,
  };
}

const ANALYTICS = new Set([
  "portfolio_viewed",
  "metric_drilldown_opened",
  "assist_opened",
  "assist_action_completed",
  "app_drag_started",
  "app_stage_change_completed",
  "app_stage_change_failed",
  "flow_filter_changed",
  "app_drawer_opened",
  "note_created",
  "theme_changed",
]);

/** Product analytics: event name, app id, and view only. Never note text or personal data. */
export function track(event: string, sourceView: string, appId?: string): void {
  if (SNAPSHOT || !ANALYTICS.has(event)) return;
  void api.post("/events", { event, source_view: sourceView, app_id: appId ?? null }).catch(() => undefined);
}

export type Theme = "dark" | "light";

function themeKey(user: string | null): string {
  return `cp.theme.${user ?? "anonymous"}`;
}

/** Theme persists per user. Switching only flips CSS tokens; it never refetches data. */
export function useTheme(user: string | null): [Theme, (t: Theme) => void] {
  const read = (): Theme => {
    try {
      return (localStorage.getItem(themeKey(user)) as Theme | null) ?? "dark";
    } catch {
      return "dark";
    }
  };
  const [theme, setTheme] = useState<Theme>(read);
  useEffect(() => setTheme(read()), [user]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);
  const update = (t: Theme) => {
    setTheme(t);
    try {
      localStorage.setItem(themeKey(user), t);
    } catch {
      // per-viewer convenience only
    }
    track("theme_changed", "topbar");
  };
  return [theme, update];
}

/** One reducer for every app mutation: patches app lists in place and refreshes the
 *  Portfolio, Flow, Assist, and detail caches so all views agree without a reload. */
export function applyAppEvent(qc: QueryClient, app: Partial<AppCard> & { app_id: string }, _event?: AppEvent): void {
  qc.setQueriesData<AppCard[]>({ queryKey: ["apps"] }, (old) =>
    old?.map((c) => (c.app_id === app.app_id ? { ...c, ...app } : c)),
  );
  for (const key of ["portfolio", "flow", "assist", "app", "reviews", "spend"]) {
    void qc.invalidateQueries({ queryKey: [key] });
  }
  void qc.invalidateQueries({ queryKey: ["apps"] });
}

export function useApplyAppEvent() {
  const qc = useQueryClient();
  return (app: Partial<AppCard> & { app_id: string }, event?: AppEvent) => applyAppEvent(qc, app, event);
}
