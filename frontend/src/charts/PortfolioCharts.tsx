// Portfolio charts, loaded lazily (Section 9A performance budget).
// Series use chart_1..chart_5 only; status colors never color a series.
import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
  Legend,
} from "recharts";
import type { MatrixPoint, PortfolioData } from "../lib/api";
import { compact, exact, label } from "../lib/format";

const AXIS = { fontSize: 11, fill: "var(--text_muted)" };
const GRID = { stroke: "var(--border)", strokeOpacity: 0.6 };
const RISK_STYLE = {
  low: { fill: "var(--chart_2)", shape: "circle" as const },
  medium: { fill: "var(--chart_3)", shape: "diamond" as const },
  high: { fill: "var(--chart_4)", shape: "triangle" as const },
};

function MatrixTip({ active, payload }: { active?: boolean; payload?: { payload: MatrixPoint }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0]!.payload;
  return (
    <div className="shadow-overlay rounded-lg border border-line bg-overlay p-3 t-label">
      <div className="t-card">{p.name}</div>
      <div className="text-muted">
        Cost {exact(p.cost, "USD")}/month (FIXTURE or MEASURED) · Value {p.value === null ? "none" : `${exact(p.value, "USD")}/month (ASSUMPTION)`}
      </div>
      <div className="text-muted">
        {label(p.risk_tier)} risk · volume {exact(p.volume)} · {p.quadrant}
      </div>
      <div className="mt-1 text-accent">Click to open the app</div>
    </div>
  );
}

export function InvestmentMatrix({ data, onOpen }: { data: PortfolioData["matrix"]; onOpen: (appId: string) => void }) {
  const tiers = (["low", "medium", "high"] as const).map((t) => ({ t, points: data.points.filter((p) => p.risk_tier === t) }));
  return (
    <ResponsiveContainer width="100%" height={232}>
      <ScatterChart margin={{ top: 8, right: 16, bottom: 24, left: 40 }}>
        <CartesianGrid {...GRID} />
        <XAxis type="number" dataKey="cost" name="Monthly cost" tick={AXIS} tickCount={6} tickFormatter={(v: number) => `$${compact(v)}`} label={{ value: "Monthly cost (USD)", position: "insideBottom", offset: -16, ...AXIS }} />
        <YAxis type="number" dataKey="value" name="Estimated value" tick={AXIS} tickCount={6} tickFormatter={(v: number) => `$${compact(v)}`} width={56} label={{ value: "Est. value (USD)", angle: -90, position: "insideLeft", offset: -24, dy: 48, ...AXIS }} />
        <ZAxis type="number" dataKey="volume" range={[40, 420]} />
        <ReferenceLine x={data.cost_split} stroke="var(--border_strong)" strokeDasharray="4 4" />
        <ReferenceLine y={data.value_split} stroke="var(--border_strong)" strokeDasharray="4 4" />
        <Tooltip content={<MatrixTip />} cursor={{ strokeDasharray: "4 4" }} />
        <Legend verticalAlign="top" height={20} iconSize={10} wrapperStyle={{ fontSize: 11 }} />
        {tiers.map(({ t, points }) => (
          <Scatter
            key={t}
            name={`${label(t)} risk`}
            data={points}
            fill={RISK_STYLE[t].fill}
            shape={RISK_STYLE[t].shape}
            animationDuration={240}
            onClick={(p: { payload?: MatrixPoint }) => p.payload && onOpen(p.payload.app_id)}
            cursor="pointer"
          />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  );
}

export function PlatformBars({ data }: { data: PortfolioData["platforms"] }) {
  const rows = data.map((d) => ({ ...d, name: label(d.platform) }));
  return (
    <ResponsiveContainer width="100%" height={150}>
      <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 24, bottom: 24, left: 32 }}>
        <CartesianGrid {...GRID} horizontal={false} />
        <XAxis xAxisId="apps" type="number" tick={AXIS} tickCount={6} hide />
        <XAxis xAxisId="spend" type="number" tick={AXIS} tickCount={5} orientation="bottom" tickFormatter={(v: number) => `$${compact(v)}`} label={{ value: "Monthly spend (USD)", position: "insideBottom", offset: -16, ...AXIS }} />
        <YAxis type="category" dataKey="name" tick={AXIS} width={72} interval={0} />
        <Tooltip
          formatter={(v, n) => (n === "Spend" ? [exact(Number(v), "USD"), n] : [v, n])}
          contentStyle={{ background: "var(--bg_overlay)", border: "1px solid var(--border)", fontSize: 12 }}
        />
        <Legend verticalAlign="top" height={20} iconSize={10} wrapperStyle={{ fontSize: 11 }} />
        <Bar xAxisId="spend" dataKey="spend" name="Spend" fill="var(--chart_1)" animationDuration={240} barSize={10} />
        <Bar xAxisId="apps" dataKey="apps" name="Apps" fill="var(--chart_5)" animationDuration={240} barSize={10} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default InvestmentMatrix;
