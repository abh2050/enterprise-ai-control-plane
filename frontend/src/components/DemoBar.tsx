// Interactive demo bar (GitHub Pages build): engine status, the identity picker, reset,
// and suggested things to try. The backend runs in this tab, so every rule the server
// enforces is enforced here too, and nothing a visitor does reaches anyone else.
import { useQueryClient } from "@tanstack/react-query";
import { BookOpen, Cpu, Lightbulb, LoaderCircle, RotateCcw, TriangleAlert } from "lucide-react";
import { useState, useSyncExternalStore } from "react";
import { api, getFixtureUser, setFixtureUser } from "../lib/api";
import { getEngineState, onEngineState } from "../lib/demo/engine";
import { Button, Select, useToast } from "./ui";

export const DEMO_IDENTITIES = [
  { value: "admin@example.com", label: "Governance admin" },
  { value: "owner@example.com", label: "App owner" },
  { value: "reviewer@example.com", label: "Reviewer" },
  { value: "security@example.com", label: "Security reviewer" },
  { value: "exec@example.com", label: "Executive viewer" },
];

const TRY = [
  "Pipeline: drag Mortgage Document Q&A from Review gates to Evaluation (its approvals are in place). Then try Meeting Notes to Business case: blocked until a business case exists.",
  "Reviews: as Governance admin, submit an app and try to approve its gate yourself. A different person must approve.",
  "Support Triage, Decision Policy tab: edit the cohort and preview the gates, recomputed from the measured results. As App owner, propose the release.",
  "Then, as Governance admin, open the Release tab and record a decision. Full activation stays blocked while gates fail.",
  "Switch to Executive viewer: write controls disappear, and the backend refuses writes anyway.",
];

export function DemoBar() {
  const engine = useSyncExternalStore(onEngineState, getEngineState);
  const qc = useQueryClient();
  const toast = useToast();
  const [who, setWho] = useState(getFixtureUser() ?? "admin@example.com");
  // First visit: show what to try without being asked.
  const [tips, setTips] = useState(() => {
    try {
      const seen = localStorage.getItem("cp.demoTipsSeen");
      localStorage.setItem("cp.demoTipsSeen", "1");
      return !seen;
    } catch {
      return true;
    }
  });
  const [resetting, setResetting] = useState(false);

  return (
    <div className="no-print border-b border-line bg-accent-soft/40 px-4 py-2 min-[720px]:px-8">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="t-label inline-flex items-center gap-2 rounded-full border border-accent px-3 py-1 text-accent">
          <Cpu size={14} strokeWidth={1.75} aria-hidden /> DEMO
        </span>
        {engine.status === "booting" && (
          <span role="status" className="t-body inline-flex items-center gap-2 text-muted">
            <LoaderCircle size={16} className="animate-spin motion-reduce:animate-none" aria-hidden />
            Starting the backend in your browser: {engine.step}. Browse now; editing unlocks in a few seconds.
          </span>
        )}
        {engine.status === "failed" && (
          <span role="alert" className="t-body inline-flex items-center gap-2 text-warning">
            <TriangleAlert size={16} aria-hidden /> The demo engine could not start in this browser, so the console is read only. ({engine.error})
          </span>
        )}
        {engine.status === "ready" && (
          <span className="t-body text-muted">
            The real backend runs in this tab. Changes stay here.
          </span>
        )}
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Select
            label="Viewing as"
            value={who}
            options={DEMO_IDENTITIES}
            onChange={(v) => {
              setWho(v);
              setFixtureUser(v);
              void qc.invalidateQueries();
            }}
          />
          <a href="../" className="m-hover t-card inline-flex min-h-11 items-center gap-2 rounded-lg px-4 text-ink hover:bg-raised sm:min-h-9">
            <BookOpen size={16} strokeWidth={1.75} aria-hidden /> About this project
          </a>
          <Button variant="ghost" icon={Lightbulb} aria-expanded={tips} onClick={() => setTips((t) => !t)}>
            Things to try
          </Button>
          <Button
            variant="ghost"
            icon={RotateCcw}
            loading={resetting}
            disabled={engine.status !== "ready"}
            onClick={async () => {
              setResetting(true);
              try {
                await api.post("/fixture/reset");
                await qc.invalidateQueries();
                toast({ kind: "success", message: "Demo reset to the starting data." });
              } finally {
                setResetting(false);
              }
            }}
          >
            Reset demo
          </Button>
        </div>
      </div>
      {tips && (
        <ul className="t-body mt-2 grid list-disc gap-x-12 gap-y-1 pl-5 text-muted min-[1280px]:grid-cols-2">
          {TRY.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
