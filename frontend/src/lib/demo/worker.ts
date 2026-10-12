/// <reference lib="webworker" />
// The interactive demo's engine: the real control plane backend running in Pyodide.
//
// Loads the vendored Python runtime and frozen packages, unpacks the backend bundle,
// and serves API requests through control_plane.browser.Bridge. Everything stays inside
// this worker: there is no network call after the files load, and nothing is stored.

interface PyProxy {
  request_json(method: string, path: string, headers: unknown, body: string | null): Promise<string>;
  start(): Promise<void>;
}

interface Pyodide {
  loadPackage(names: string[], opts?: { messageCallback?: (m: string) => void }): Promise<void>;
  unpackArchive(buffer: ArrayBuffer, format: string, opts: { extractDir: string }): void;
  runPythonAsync(code: string): Promise<unknown>;
  toPy(value: unknown): unknown;
  globals: { get(name: string): PyProxy; set(name: string, value: unknown): void };
}

export type EngineMessage =
  | { type: "progress"; step: string }
  | { type: "ready"; ms: number }
  | { type: "failed"; error: string }
  | { type: "response"; id: number; status: number; body: string };

export type EngineRequest =
  | { type: "boot"; base: string; fixedNow: string }
  | { type: "request"; id: number; method: string; path: string; headers: Record<string, string>; body: string | null };

const BOOT = `
import os, sys
sys.path.insert(0, "/app/backend")
os.chdir("/app")
os.environ.update(demo_env)
from control_plane.api import create_app
from control_plane.browser import Bridge
bridge = Bridge(create_app())
`;

let bridge: PyProxy | null = null;
let py: Pyodide | null = null;
const post = (m: EngineMessage) => (self as unknown as DedicatedWorkerGlobalScope).postMessage(m);

async function sha256(buf: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", buf);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function boot(base: string, fixedNow: string): Promise<void> {
  const started = performance.now();
  post({ type: "progress", step: "Loading Python" });
  const runtime = `${base}pyodide/`;
  const { loadPyodide } = (await import(/* @vite-ignore */ `${runtime}pyodide.mjs`)) as {
    loadPyodide(opts: Record<string, unknown>): Promise<Pyodide>;
  };
  py = await loadPyodide({ indexURL: runtime, lockFileURL: `${runtime}pyodide-lock.json`, stdout: () => {}, stderr: () => {} });
  post({ type: "progress", step: "Loading packages" });
  const packages = (await (await fetch(`${runtime}packages.json`)).json()) as string[];
  await py.loadPackage(packages, { messageCallback: () => {} });
  post({ type: "progress", step: "Loading the backend" });
  const manifest = (await (await fetch(`${base}manifest.json`)).json()) as { bundle: string; sha256: string };
  const zip = await (await fetch(`${base}${manifest.bundle}`)).arrayBuffer();
  if ((await sha256(zip)) !== manifest.sha256) throw new Error("backend bundle failed its integrity check");
  py.unpackArchive(zip, "zip", { extractDir: "/app" });
  py.globals.set(
    "demo_env",
    py.toPy({ BIND_HOST: "browser", IDENTITY_MODE: "fixture", STORE_BACKEND: "memory", PROVIDER_MODE: "fixture", FIXED_NOW: fixedNow }),
  );
  await py.runPythonAsync(BOOT);
  post({ type: "progress", step: "Seeding the registry" });
  bridge = py.globals.get("bridge");
  await bridge.start();
  post({ type: "ready", ms: Math.round(performance.now() - started) });
}

// Requests are handled one at a time, in arrival order, like a single-worker server.
let queue: Promise<void> = Promise.resolve();

self.onmessage = (e: MessageEvent<EngineRequest>) => {
  const msg = e.data;
  if (msg.type === "boot") {
    boot(msg.base, msg.fixedNow).catch((err: unknown) => post({ type: "failed", error: String(err) }));
    return;
  }
  queue = queue.then(async () => {
    try {
      if (!bridge || !py) throw new Error("engine not ready");
      const raw = await bridge.request_json(msg.method, msg.path, py.toPy(msg.headers), msg.body);
      const res = JSON.parse(raw) as { status: number; body: string };
      post({ type: "response", id: msg.id, status: res.status, body: res.body });
    } catch (err) {
      post({ type: "response", id: msg.id, status: 500, body: JSON.stringify({ detail: String(err) }) });
    }
  });
};
