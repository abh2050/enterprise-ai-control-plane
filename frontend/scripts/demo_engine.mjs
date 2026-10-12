// Run the demo engine (the real backend in Pyodide) under Node.
//
//   node scripts/demo_engine.mjs SCENARIO.json OUT.json
//
// Boots the vendored Pyodide exactly as the browser worker does, replays a scenario of API requests
// through control_plane.browser.Bridge, and writes the responses. The parity test
// (tests/test_demo_parity.py) compares them with the native backend's responses.
import { loadPyodide } from "pyodide";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const demoDir = join(here, "..", ".demo-data", "demo");
const [scenarioPath, outPath] = process.argv.slice(2);
if (!scenarioPath || !outPath) throw new Error("usage: demo_engine.mjs SCENARIO.json OUT.json");
const scenario = JSON.parse(readFileSync(scenarioPath, "utf8"));
const manifest = JSON.parse(readFileSync(join(demoDir, "manifest.json"), "utf8"));

// Load only the vendored runtime and frozen packages (scripts/vendor_pyodide.mjs), as the
// browser does, so the parity test covers exactly what ships.
const vendored = join(demoDir, "pyodide");
const py = await loadPyodide({
  indexURL: vendored + "/",
  lockFileURL: join(vendored, "pyodide-lock.json"),
  stdout: () => {},
  stderr: (s) => process.stderr.write(s + "\n"),
});
await py.loadPackage(JSON.parse(readFileSync(join(vendored, "packages.json"), "utf8")), { messageCallback: () => {} });
py.unpackArchive(new Uint8Array(readFileSync(join(demoDir, manifest.bundle))), "zip", { extractDir: "/app" });

const env = { ...scenario.env, BIND_HOST: "browser", IDENTITY_MODE: "fixture", STORE_BACKEND: "memory", PROVIDER_MODE: "fixture" };
py.globals.set("demo_env", py.toPy(env));
await py.runPythonAsync(`
import os, sys
sys.path.insert(0, "/app/backend")
os.chdir("/app")
os.environ.update(demo_env)
from control_plane.api import create_app
from control_plane.browser import Bridge
bridge = Bridge(create_app())
`);
const bridge = py.globals.get("bridge");
const results = [];
const vars = {};
for (const step of scenario.steps) {
  const headers = step.user ? { "X-Fixture-User": step.user } : {};
  const path = step.path.replace(/\{(\w+)\}/g, (_, k) => vars[k]);
  // "{name}" values in a body take the captured value, keeping its JSON type.
  const body = step.body ? JSON.stringify(step.body).replace(/"\{(\w+)\}"/g, (_, k) => JSON.stringify(vars[k])) : null;
  const res = JSON.parse(await bridge.request_json(step.method, path, py.toPy(headers), body));
  for (const [name, key] of Object.entries(step.capture ?? {})) vars[name] = key.split(".").reduce((v, k) => v[k], JSON.parse(res.body));
  results.push({ name: step.name, status: res.status, body: res.body });
}
writeFileSync(outPath, JSON.stringify(results));
console.log(`demo engine: ${results.length} requests replayed`);
