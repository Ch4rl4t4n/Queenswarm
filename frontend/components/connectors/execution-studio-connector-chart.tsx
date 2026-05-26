"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface ConnectorChartDatum {
  slug: string;
  runs: number;
  blocks: number;
}

interface ExecutionStudioConnectorChartProps {
  data: ConnectorChartDatum[];
}

/** Per-connector tool runs vs cost-tier blocks — cyan + magenta bars. */
export function ExecutionStudioConnectorChart({ data }: ExecutionStudioConnectorChartProps) {
  if (data.length === 0) {
    return null;
  }

  const chartData = data.map((row) => ({
    ...row,
    label: row.slug.length > 16 ? `${row.slug.slice(0, 14)}…` : row.slug,
  }));

  return (
    <div className="h-56 w-full rounded-xl border border-[color:var(--qs-border-2)]/15 bg-black/35 p-3">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 6" stroke="rgb(0 255 255 / 0.08)" />
          <XAxis
            dataKey="label"
            tick={{ fill: "#71717a", fontSize: 9 }}
            axisLine={{ stroke: "rgb(0 255 255 / 0.12)" }}
            interval={0}
            angle={-18}
            textAnchor="end"
            height={48}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: "#71717a", fontSize: 10 }}
            axisLine={{ stroke: "rgb(0 255 255 / 0.12)" }}
          />
          <Tooltip
            contentStyle={{
              background: "#121214",
              border: "1px solid rgb(0 255 255 / 0.35)",
              borderRadius: "10px",
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "12px",
            }}
            labelFormatter={(_label, payload) => {
              const row = payload?.[0]?.payload as ConnectorChartDatum | undefined;
              return row?.slug ?? _label;
            }}
          />
          <Legend wrapperStyle={{ fontSize: "11px", color: "#a1a1aa" }} />
          <Bar dataKey="runs" name="Runs" fill="#00FFFF" radius={[4, 4, 0, 0]} maxBarSize={28} isAnimationActive={false} />
          <Bar dataKey="blocks" name="Blocked" fill="#FF00AA" radius={[4, 4, 0, 0]} maxBarSize={28} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
