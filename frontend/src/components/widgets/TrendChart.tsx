import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { TrendPoint } from "../../types/scan";

function formatTs(ts: string) {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString();
}

export function TrendChart({ points }: { points: TrendPoint[] }) {
  const data = (points || []).map((p) => ({
    ts: p.ts,
    label: formatTs(p.ts),
    final_score: p.final_score,
    issues: p.issues,
    loc: p.loc,
  }));

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold">Risk Trend</div>
        <div className="text-xs text-white/50">Score over time</div>
      </div>

      <div className="mt-4 h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="4 4" opacity={0.15} />
            <XAxis dataKey="label" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
            <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
            <Tooltip
              contentStyle={{
                background: "rgba(24,24,27,0.95)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 12,
              }}
              labelFormatter={(v) => String(v)}
              formatter={(value: any, name: any) => [value, name]}
            />
            <Line type="monotone" dataKey="final_score" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}