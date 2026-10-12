import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, HashRouter, Navigate, Route, Routes } from "react-router";
import { Shell } from "./components/Shell";
import { Skeleton, ToastProvider } from "./components/ui";
import "./index.css";
import { DEMO, getFixtureUser, setFixtureUser, snapshotFile, STATIC_SITE } from "./lib/api";
import { bootEngine, engineReady } from "./lib/demo/engine";
import { setClock } from "./lib/clock";
import Portfolio from "./pages/Portfolio";

const Pipeline = lazy(() => import("./pages/Pipeline"));
const Flow = lazy(() => import("./pages/Flow"));
const Applications = lazy(() => import("./pages/Applications"));
const AppDetail = lazy(() => import("./pages/AppDetail"));
const Reviews = lazy(() => import("./pages/Reviews"));
const Incidents = lazy(() => import("./pages/Incidents"));
const Settings = lazy(() => import("./pages/Settings"));

if (STATIC_SITE) {
  // Pin the clock to the export time before anything renders.
  const meta = await fetch(`${import.meta.env.BASE_URL}${snapshotFile("/meta")}`).then((r) => r.json() as Promise<{ generated_at: string }>);
  setClock(meta.generated_at);
  if (DEMO) {
    // The engine runs on the same clock, so its answers match the exported first paint.
    if (!getFixtureUser()) setFixtureUser("admin@example.com");
    bootEngine(meta.generated_at);
  }
}

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false, staleTime: 30_000 } },
});
// The first paint came from exported files; once the engine runs, refetch everything from it.
if (DEMO) void engineReady.then(() => queryClient.invalidateQueries());

// The snapshot and the demo are served from static hosting, so they route with the URL hash.
const Router = STATIC_SITE ? HashRouter : BrowserRouter;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <Router>
          <Routes>
            <Route element={<Shell />}>
              <Route index element={<Navigate to="/portfolio" replace />} />
              <Route path="portfolio" element={<Portfolio />} />
              {[
                ["pipeline", <Pipeline key="p" />],
                ["flow", <Flow key="f" />],
                ["apps", <Applications key="a" />],
                ["apps/:appId", <AppDetail key="d" />],
                ["reviews", <Reviews key="r" />],
                ["incidents", <Incidents key="i" />],
                ["settings", <Settings key="s" />],
              ].map(([path, el]) => (
                <Route key={path as string} path={path as string} element={<Suspense fallback={<Skeleton className="h-96" />}>{el}</Suspense>} />
              ))}
            </Route>
          </Routes>
        </Router>
      </ToastProvider>
    </QueryClientProvider>
  </StrictMode>,
);
