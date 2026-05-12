"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface SpendDayDatum {
  day: string;
  spend_usd: number;
}

interface SpendTrendChartProps {
  data: SpendDayDatum[];
}

/** Verified operator spend curve — amber stroke per Costs mockups. */
export function SpendTrendChart({ data }: SpendTrendChartProps) {
  return (
    <div className="h-72 w-full rounded-xl border border-cyan/15 bg-black/35 p-3">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#FFB800" stopOpacity={0.45} />
              <stop offset="100%" stopColor="#FFB800" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 6" stroke="rgb(0 255 255 / 0.08)" />
          <XAxis dataKey="day" tick={{ fill: "#71717a", fontSize: 10 }} axisLine={{ stroke: "rgb(0 255 255 / 0.12)" }} />
          <YAxis
            tick={{ fill: "#71717a", fontSize: 10 }}
            axisLine={{ stroke: "rgb(0 255 255 / 0.12)" }}
            tickFormatter={(v) => `$${v}`}
          />
          <Tooltip
            formatter={(value: number) => [`$${value.toFixed(2)}`, "Spend"]}
            contentStyle={{
              background: "#121214",
              border: "1px solid rgb(255 184 0 / 0.35)",
              borderRadius: "10px",
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "12px",
            }}
          />
          <Area
            type="monotone"
            dataKey="spend_usd"
            stroke="#FFB800"
            strokeWidth={2}
            fill="url(#spendGrad)"
            dot={false}
            activeDot={{ r: 4, stroke: "#00ffff", strokeWidth: 2, fill: "#FFB800" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
