// Main-thread side of the interactive demo engine (see worker.ts).
//
// Boots the worker once, reports progress to subscribers, and forwards API requests.
// Requests sent before the engine is ready wait for it.
import type { EngineMessage, EngineRequest } from "./worker";

export type EngineState =
  | { status: "booting"; step: string }
  | { status: "ready"; ms: number }
  | { status: "failed"; error: string };

let worker: Worker | null = null;
let state: EngineState = { status: "booting", step: "Starting" };
let nextId = 1;
const pending = new Map<number, (r: { status: number; body: string }) => void>();
const listeners = new Set<(s: EngineState) => void>();
let resolveReady: () => void;
let rejectReady: (e: Error) => void;
export const engineReady = new Promise<void>((resolve, reject) => {
  resolveReady = resolve;
  rejectReady = reject;
});
engineReady.catch(() => {}); // failures surface through the state, not as unhandled rejections

function setState(next: EngineState): void {
  state = next;
  for (const l of listeners) l(state);
}

export function getEngineState(): EngineState {
  return state;
}

export function onEngineState(listener: (s: EngineState) => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function bootEngine(fixedNow: string): void {
  if (worker) return;
  worker = new Worker(new URL("./worker.ts", import.meta.url), { type: "module" });
  worker.onmessage = (e: MessageEvent<EngineMessage>) => {
    const m = e.data;
    if (m.type === "progress") setState({ status: "booting", step: m.step });
    else if (m.type === "ready") {
      setState({ status: "ready", ms: m.ms });
      resolveReady();
    } else if (m.type === "failed") {
      setState({ status: "failed", error: m.error });
      rejectReady(new Error(m.error));
    } else {
      pending.get(m.id)?.(m);
      pending.delete(m.id);
    }
  };
  worker.onerror = (e) => {
    setState({ status: "failed", error: e.message || "the demo engine could not start" });
    rejectReady(new Error(e.message));
  };
  const base = new URL(`${import.meta.env.BASE_URL}demo/`, window.location.href).href;
  const msg: EngineRequest = { type: "boot", base, fixedNow };
  worker.postMessage(msg);
}

export async function engineRequest(
  method: string,
  path: string,
  headers: Record<string, string>,
  body: string | null,
): Promise<{ status: number; body: string }> {
  await engineReady;
  const id = nextId++;
  return new Promise((resolve) => {
    pending.set(id, resolve);
    const msg: EngineRequest = { type: "request", id, method, path: `/api${path}`, headers, body };
    worker!.postMessage(msg);
  });
}
