// Vendor the Python runtime for the in-browser demo into .demo-data/demo/pyodide/.
//
//   node scripts/vendor_pyodide.mjs
//
// Resolves the demo's packages once (Pyodide's prebuilt set plus the pure-Python wheels
// pinned in .demo-data/demo/manifest.json), freezes the result into a trimmed
// pyodide-lock.json, and copies or downloads every file, checking each one's SHA-256
// against the lock. The browser then loads only these files: no CDN or PyPI at runtime.
import { setDefaultResultOrder } from "node:dns";
import { loadPyodide } from "pyodide";
import { copyFileSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { basename, dirname, join } from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const demoDir = join(here, "..", ".demo-data", "demo");
const outDir = join(demoDir, "pyodide");
const pyodideDir = dirname(createRequire(import.meta.url).resolve("pyodide/package.json"));
const manifest = JSON.parse(readFileSync(join(demoDir, "manifest.json"), "utf8"));
const CORE = ["pyodide.mjs", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip"];
const CDN = `https://cdn.jsdelivr.net/pyodide/v${JSON.parse(readFileSync(join(pyodideDir, "package.json"), "utf8")).version}/full/`;

// Some networks have no working IPv6 route; prefer IPv4 for the downloads below.
setDefaultResultOrder("ipv4first");

// Skip when the vendored set already matches the pinned inputs: builds stay offline and fast.
const version = JSON.parse(readFileSync(join(pyodideDir, "package.json"), "utf8")).version;
const stamp = JSON.stringify({ version, requirements: manifest.requirements, packages: manifest.pyodide_packages });
const stampFile = join(outDir, "vendor-stamp.json");
if (existsSync(stampFile) && readFileSync(stampFile, "utf8") === stamp && existsSync(join(outDir, "pyodide-lock.json"))) {
  console.log(`vendored runtime is current (${outDir}); skipping`);
  process.exit(0);
}

const py = await loadPyodide({ stdout: () => {}, stderr: () => {} });
await py.loadPackage(manifest.pyodide_packages, { messageCallback: () => {} });
const micropip = py.pyimport("micropip");
await micropip.install(manifest.requirements);
const lock = JSON.parse(micropip.freeze());

// Everything loaded except micropip and what only it needs.
const runtimeOnly = new Set(["micropip", "packaging"]);
const names = Object.keys(py.loadedPackages).filter((n) => !runtimeOnly.has(n));
rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });

const sha256 = (buf) => createHash("sha256").update(buf).digest("hex");
const packages = {};
for (const name of names) {
  const key = Object.keys(lock.packages).find((k) => lock.packages[k].name === name || k === name);
  if (!key) throw new Error(`${name} is loaded but missing from the frozen lock`);
  const entry = { ...lock.packages[key] };
  const file = basename(new URL(entry.file_name, CDN).pathname);
  let data;
  const local = join(pyodideDir, file);
  if (existsSync(local)) data = readFileSync(local);
  else {
    const res = await fetch(new URL(entry.file_name, CDN));
    if (!res.ok) throw new Error(`download failed for ${file}: ${res.status}`);
    data = Buffer.from(await res.arrayBuffer());
  }
  if (sha256(data) !== entry.sha256) throw new Error(`sha256 mismatch for ${file}`);
  writeFileSync(join(outDir, file), data);
  entry.file_name = file;
  entry.depends = entry.depends.filter((d) => !runtimeOnly.has(d));
  packages[key] = entry;
}
for (const f of CORE) copyFileSync(join(pyodideDir, f), join(outDir, f));
// Node (the parity test) must read pyodide.asm.js as CommonJS; browsers ignore this file.
writeFileSync(join(outDir, "package.json"), '{ "type": "commonjs" }\n');
writeFileSync(join(outDir, "pyodide-lock.json"), JSON.stringify({ info: lock.info, packages }, null, 1) + "\n");
writeFileSync(join(outDir, "packages.json"), JSON.stringify(Object.keys(packages).sort()) + "\n");
writeFileSync(stampFile, stamp);
console.log(`vendored ${Object.keys(packages).length} packages + runtime into ${outDir}`);
