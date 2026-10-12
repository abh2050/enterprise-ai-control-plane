import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, HashRouter, Navigate, Route, Routes } from "react-router";
import { Shell } from "./components/Shell";
import { Skeleton, ToastProvider } from "./components/ui";
import "./index.css";
import { SNAPSHOT } from "./lib/api";
import Portfolio from "./pages/Portfolio";

const Pipeline = lazy(() => import("./pages/Pipeline"));
const Flow = lazy(() => import("./pages/Flow"));
const Applications = lazy(() => import("./pages/Applications"));
const AppDetail = lazy(() => import("./pages/AppDetail"));
const Reviews = lazy(() => import("./pages/Reviews"));
const Incidents = lazy(() => import("./pages/Incidents"));
const Settings = lazy(() => import("./pages/Settings"));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false, staleTime: 30_000 } },
});

// The snapshot is served from static hosting, so it routes with the URL hash.
const Router = SNAPSHOT ? HashRouter : BrowserRouter;

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
