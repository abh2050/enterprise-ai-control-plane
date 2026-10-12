// Number and date formatting (console spec Section 9A).
// Compact: 1,000 -> 1.0k and 1,000,000 -> 1.0m. Exact values go in tooltips and labels.

export function compact(n: number): string {
  const abs = Math.abs(n);
  const sign = n < 0 ? "−" : "";
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(1)}m`;
  if (abs >= 1_000) return `${sign}${(abs / 1_000).toFixed(1)}k`;
  return `${sign}${Number.isInteger(abs) ? abs : abs.toFixed(2)}`;
}

export function exact(n: number, unit = ""): string {
  const usd = unit.startsWith("USD");
  const digits = usd && Math.abs(n) < 100 && !Number.isInteger(n) ? 2 : 0;
  const s = Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: Math.max(digits, n % 1 ? 2 : 0) });
  return `${n < 0 ? "−" : ""}${usd ? "$" : ""}${s}`;
}

export function money(n: number | null): string {
  if (n === null) return "—";
  if (Math.abs(n) < 100 && !Number.isInteger(n)) return `$${n.toFixed(2)}`;
  return `${n < 0 ? "−" : ""}$${compact(Math.abs(n))}`;
}

export function pct(ratio: number | null): string {
  return ratio === null ? "—" : `${(ratio * 100).toFixed(1)}%`;
}

export function days(n: number | null): string {
  return n === null ? "—" : `${Math.round(n)}d`;
}

export function metricText(value: number | null, unit: string): string {
  if (value === null) return "—";
  if (unit.startsWith("USD")) return money(value);
  if (unit === "ratio") return pct(value);
  if (unit === "days") return days(value);
  return compact(value);
}

export function exactMetric(value: number | null, unit: string): string {
  if (value === null) return "No value";
  if (unit === "ratio") return `${(value * 100).toFixed(2)}%`;
  return `${exact(value, unit)} ${unit.startsWith("USD") ? unit.replace(/^USD\/?/, "per ").replace("per USD", "") : unit}`.trim();
}

const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

export function relative(iso: string | null, now: Date = new Date()): string {
  if (!iso) return "never";
  const diff = (new Date(iso).getTime() - now.getTime()) / 1000;
  const abs = Math.abs(diff);
  if (abs < 60) return rtf.format(Math.round(diff), "second");
  if (abs < 3600) return rtf.format(Math.round(diff / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(diff / 3600), "hour");
  return rtf.format(Math.round(diff / 86400), "day");
}

export function timestamp(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
}

export const label = (s: string): string => s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
