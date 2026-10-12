// The console's display clock. A snapshot pins it to the export time so relative dates and
// freshness read the same whenever the static site is opened. Visual tests pin it the same
// way through a local override. It changes how times render, never what data is loaded.
let offsetMs = 0;

export function setClock(at: string): void {
  offsetMs = new Date(at).getTime() - Date.now();
}

try {
  const pinned = localStorage.getItem("cp.displayClock");
  if (pinned) setClock(pinned);
} catch {
  // storage unavailable: use the real clock
}

export function now(): number {
  return Date.now() + offsetMs;
}
