// Shadow and monitoring charts, loaded lazily. Series use chart_1..chart_5 only.
import { Bar, CartesianGrid, ComposedChart, Legend, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const AXIS = { fontSize: 11, fill: "var(--text_muted)" };
const TIP = { background: "var(--bg_overlay)", border: "1px solid var(--border)", fontSize: 12 };

export interface ShadowDay {
  day: number;
  cases: number;
  label_agreement: number;
  route_agreement: number;
  candidate_cost_usd: number;
  net_value_usd: { approved: number; candidate: number; cohort: number };
  accuracy: { approved: number; candidate: number; cohort: number };
}

export function AgreementChart({ days }: { days: ShadowDay[] }) {
  const rows = days.map((d) => ({ day: `Day ${d.day}`, label: +(d.label_agreement * 100).toFixed(1), route: +(d.route_agreement * 100).toFixed(1), cost: +d.candidate_cost_usd.toFixed(4) }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <ComposedChart data={rows} margin={{ top: 8, right: 40, bottom: 24, left: 32 }}>
        <CartesianGrid stroke="var(--border)" strokeOpacity={0.6} vertical={false} />
        <XAxis dataKey="day" tick={AXIS} interval={1} label={{ value: "Simulated day", position: "insideBottom", offset: -16, ...AXIS }} />
        <YAxis yAxisId="pct" tick={AXIS} tickCount={6} domain={[0, 100]} unit="%" label={{ value: "Agreement", angle: -90, position: "insideLeft", offset: -16, ...AXIS }} />
        <YAxis yAxisId="usd" orientation="right" tick={AXIS} tickCount={5} tickFormatter={(v: number) => `$${v.toFixed(2)}`} />
        <Tooltip contentStyle={TIP} />
        <Legend verticalAlign="top" height={20} iconSize={10} wrapperStyle={{ fontSize: 11 }} />
        <Bar yAxisId="usd" dataKey="cost" name="Candidate cost (USD)" fill="var(--chart_5)" animationDuration={240} />
        <Line yAxisId="pct" dataKey="label" name="Label agreement %" stroke="var(--chart_1)" strokeWidth={2} dot={false} animationDuration={240} />
        <Line yAxisId="pct" dataKey="route" name="Route agreement %" stroke="var(--chart_2)" strokeWidth={2} dot={false} animationDuration={240} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export function ValueChart({ days }: { days: ShadowDay[] }) {
  const rows = days.map((d) => ({ day: `Day ${d.day}`, classifier: Math.round(d.net_value_usd.approved), cohort: Math.round(d.net_value_usd.cohort), candidate: Math.round(d.net_value_usd.candidate) }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 24, left: 40 }}>
        <CartesianGrid stroke="var(--border)" strokeOpacity={0.6} vertical={false} />
        <XAxis dataKey="day" tick={AXIS} interval={1} label={{ value: "Simulated day", position: "insideBottom", offset: -16, ...AXIS }} />
        <YAxis tick={AXIS} tickCount={6} tickFormatter={(v: number) => `$${v}`} label={{ value: "Net value (USD)", angle: -90, position: "insideLeft", offset: -24, ...AXIS }} />
        <Tooltip contentStyle={TIP} />
        <Legend verticalAlign="top" height={20} iconSize={10} wrapperStyle={{ fontSize: 11 }} />
        <Line dataKey="classifier" name="Classifier alone" stroke="var(--chart_5)" strokeWidth={2} dot={false} animationDuration={240} />
        <Line dataKey="cohort" name="Proposed cohort" stroke="var(--chart_1)" strokeWidth={2} dot={false} animationDuration={240} />
        <Line dataKey="candidate" name="Full candidate" stroke="var(--chart_3)" strokeWidth={2} dot={false} strokeDasharray="4 3" animationDuration={240} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export interface SignalDay {
  day: number;
  review_rate: number;
  cost_per_correct_usd: number | null;
  sampled_accuracy: number | null;
  authority: string;
  drift_cases: number;
}

export function SignalChart({
  days,
  field,
  threshold,
  label,
  unit,
  drillDays,
  incidentDay,
}: {
  days: SignalDay[];
  field: "review_rate" | "cost_per_correct_usd" | "sampled_accuracy";
  threshold: number;
  label: string;
  unit: "pct" | "usd";
  drillDays: number[];
  incidentDay: number | null;
}) {
  const scale = unit === "pct" ? 100 : 1;
  const rows = days.map((d) => ({ day: d.day, value: d[field] === null ? null : +((d[field] as number) * scale).toFixed(3), paused: d.authority === "manual" }));
  const fmt = (v: number) => (unit === "pct" ? `${v.toFixed(0)}%` : `$${v.toFixed(2)}`);
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 24, left: 40 }}>
        <CartesianGrid stroke="var(--border)" strokeOpacity={0.6} vertical={false} />
        <ReferenceArea x1={drillDays[0]} x2={drillDays[drillDays.length - 1]} fill="var(--chart_4)" fillOpacity={0.12} />
        <XAxis dataKey="day" type="number" domain={[1, 14]} ticks={[1, 4, 7, 10, 12, 14]} tick={AXIS} label={{ value: "Simulated day", position: "insideBottom", offset: -16, ...AXIS }} />
        <YAxis tick={AXIS} tickCount={6} tickFormatter={fmt} label={{ value: label, angle: -90, position: "insideLeft", offset: -28, ...AXIS }} />
        <Tooltip contentStyle={TIP} formatter={(v) => (v === null ? "paused" : fmt(Number(v)))} labelFormatter={(d) => `Day ${d}`} />
        <ReferenceLine y={threshold * scale} stroke="var(--chart_3)" strokeDasharray="6 4" label={{ value: `Alert ${fmt(threshold * scale)}`, position: "insideTopRight", ...AXIS }} />
        {incidentDay !== null && <ReferenceLine x={incidentDay} stroke="var(--chart_4)" label={{ value: "Incident", position: "insideTopLeft", ...AXIS }} />}
        <Line dataKey="value" name={label} stroke="var(--chart_1)" strokeWidth={2} connectNulls={false} animationDuration={240} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export default AgreementChart;
