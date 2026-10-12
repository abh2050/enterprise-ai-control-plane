// WCAG 2.2 AA contrast check for the console tokens (console spec Section 9A).
// Text pairs need 4.5:1; UI boundaries (control borders, focus ring) need 3:1.
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../src/styles/tokens.css", import.meta.url), "utf8");
function block(selector) {
  const start = css.indexOf(selector);
  const body = css.slice(css.indexOf("{", start) + 1, css.indexOf("}", start));
  return Object.fromEntries([...body.matchAll(/--([a-z0-9_]+):\s*(#[0-9a-fA-F]{6})/g)].map((m) => [m[1], m[2]]));
}
const lum = (hex) => {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

const surfaces = ["bg_canvas", "bg_surface", "bg_raised", "bg_overlay"];
const text = ["text_primary", "text_muted", "accent", "status_healthy", "status_warning", "status_danger", "status_info"];
const boundaries = ["border_strong", "focus", "accent"];
let failures = 0;
for (const [theme, sel] of [["dark", ':root[data-theme="dark"]'], ["light", ":root {"]]) {
  const t = block(sel);
  for (const fg of text) for (const bg of surfaces) {
    const r = ratio(t[fg], t[bg]);
    if (r < 4.5) { failures++; console.log(`FAIL ${theme} text ${fg} ${t[fg]} on ${bg} ${t[bg]}: ${r.toFixed(2)}`); }
  }
  for (const fg of boundaries) for (const bg of surfaces) {
    const r = ratio(t[fg], t[bg]);
    if (r < 3) { failures++; console.log(`FAIL ${theme} boundary ${fg} ${t[fg]} on ${bg} ${t[bg]}: ${r.toFixed(2)}`); }
  }
  // Text on accent buttons
  const onAccent = ratio(t.accent_contrast ?? "#ffffff", t.accent);
  if (onAccent < 4.5) { failures++; console.log(`FAIL ${theme} accent_contrast on accent: ${onAccent.toFixed(2)}`); }
}
console.log(failures ? `${failures} failing pairs` : "All token pairs pass WCAG 2.2 AA");
process.exit(failures ? 1 : 0);
