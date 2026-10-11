import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";
import { AppShell } from "./components/AppShell";
import "./index.css";
import AppDetail from "./pages/AppDetail";
import Flow from "./pages/Flow";
import Incidents from "./pages/Incidents";
import Pipeline from "./pages/Pipeline";
import Portfolio from "./pages/Portfolio";
import Reviews from "./pages/Reviews";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<Portfolio />} />
            <Route path="pipeline" element={<Pipeline />} />
            <Route path="flow" element={<Flow />} />
            <Route path="apps/:appId" element={<AppDetail />} />
            <Route path="reviews" element={<Reviews />} />
            <Route path="incidents" element={<Incidents />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
