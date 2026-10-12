// Flow page charts, loaded lazily.
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Sankey, Tooltip, XAxis, YAxis } from "recharts";
import { label } from "../lib/format";

const AXIS = { fontSize: 11, fill: "var(--text_muted)" };

export interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

export function StageSankey({ links, onSelect }: { links: SankeyLink[]; onSelect: (stage: string) => void }) {
  // Recharts needs an acyclic graph; prefix targets that point backwards in the lifecycle.
  const names: string[] = [];
  const idx = (n: string) => {
    let i = names.indexOf(n);
    if (i < 0) {
      names.push(n);
      i = names.length - 1;
    }
    return i;
  };
  const order = ["intake", "business_case", "review_gates", "evaluation", "shadow", "controlled_activation", "monitored", "paused", "retired"];
  const data = {
    nodes: [] as { name: string }[],
    links: links
      .filter((l) => l.source !== l.target)
      .map((l) => {
        const backwards = order.indexOf(l.target) <= order.indexOf(l.source);
        return { source: idx(l.source), target: idx(backwards ? `${l.target} (returned)` : l.target), value: l.value };
      }),
  };
  data.nodes = names.map((n) => ({ name: n }));
  return (
    <ResponsiveContainer width="100%" height={300}>
      <Sankey
        data={data}
        nodePadding={18}
        margin={{ top: 8, right: 170, bottom: 24, left: 32 }}
        link={{ stroke: "var(--chart_1)", strokeOpacity: 0.35 }}
        node={({ x, y, width, height, payload }: { x: number; y: number; width: number; height: number; payload: { name: string } }) => (
          <g style={{ cursor: "pointer" }} onClick={() => onSelect(payload.name.replace(" (returned)", ""))}>
            <rect x={x} y={y} width={width} height={height} fill="var(--chart_1)" rx={2} />
            <text x={x + width + 6} y={y + height / 2} dy={4} fontSize={11} fill="var(--text_primary)">
              {label(payload.name)}
            </text>
          </g>
        )}
      >
        <Tooltip contentStyle={{ background: "var(--bg_overlay)", border: "1px solid var(--border)", fontSize: 12 }} />
      </Sankey>
    </ResponsiveContainer>
  );
}

export function WeeklyInOut({
  weeks,
  prior,
  onSelect,
}: {
  weeks: { week_start: string; in: number; out: number }[];
  prior: { in: number }[];
  onSelect: (week: string) => void;
}) {
  const rows = weeks.map((w, i) => ({ ...w, prior_in: prior[i]?.in ?? null }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <ComposedChart data={rows} margin={{ top: 8, right: 16, bottom: 24, left: 32 }} onClick={(s) => {
        if (s?.activeLabel !== undefined) onSelect(String(s.activeLabel));
      }}>
        <CartesianGrid stroke="var(--border)" strokeOpacity={0.6} vertical={false} />
        <XAxis dataKey="week_start" tick={AXIS} tickCount={6} interval="preserveStartEnd" label={{ value: "Week starting", position: "insideBottom", offset: -16, ...AXIS }} />
        <YAxis tick={AXIS} tickCount={6} allowDecimals={false} label={{ value: "Apps", angle: -90, position: "insideLeft", offset: -16, ...AXIS }} />
        <Tooltip contentStyle={{ background: "var(--bg_overlay)", border: "1px solid var(--border)", fontSize: 12 }} />
        <Legend verticalAlign="top" height={20} iconSize={10} wrapperStyle={{ fontSize: 11 }} />
        <Bar dataKey="in" name="Entered intake" fill="var(--chart_1)" animationDuration={240} cursor="pointer" />
        <Bar dataKey="out" name="Retired" fill="var(--chart_3)" animationDuration={240} cursor="pointer" />
        <Line dataKey="prior_in" name="Entered, prior period" stroke="var(--chart_5)" strokeWidth={1} dot={false} animationDuration={240} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export default StageSankey;
