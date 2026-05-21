"use client";

import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface AuditRollupTrendDatum {
  date: string;
  action_count: number;
  tenants_active: number;
}

interface AuditRollupTrendChartProps {
  data: AuditRollupTrendDatum[];
}

function shortDay(isoDate: string): string {
  const parsed = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) {
    return isoDate.slice(5);
  }
  return parsed.toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" });
}

/** Compact 7-day supervisor operator audit trend for command center. */
export function AuditRollupTrendChart({ data }: AuditRollupTrendChartProps) {
  const chartData = data.map((point) => ({
    ...point,
    label: shortDay(point.date),
  }));

  return (
    <div className="h-36 w-full rounded-xl border border-[color:var(--qs-border-2)]/15 bg-black/35 p-3">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="auditRollupGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00FFFF" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#00FFFF" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="label"
            tick={{ fill: "#71717a", fontSize: 10 }}
            axisLine={{ stroke: "rgb(0 255 255 / 0.12)" }}
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            width={28}
            tick={{ fill: "#71717a", fontSize: 10 }}
            axisLine={{ stroke: "rgb(0 255 255 / 0.12)" }}
            tickLine={false}
          />
          <Tooltip
            formatter={(value: number, name: string) => [
              value,
              name === "action_count" ? "Actions" : "Active hives",
            ]}
            labelFormatter={(_, payload) => {
              const row = payload?.[0]?.payload as AuditRollupTrendDatum | undefined;
              return row?.date ?? "";
            }}
            contentStyle={{
              background: "#121214",
              border: "1px solid rgb(0 255 255 / 0.35)",
              borderRadius: "10px",
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "12px",
            }}
          />
          <Area
            type="monotone"
            dataKey="action_count"
            stroke="#00FFFF"
            strokeWidth={2}
            fill="url(#auditRollupGrad)"
            dot={{ r: 2, fill: "#FFB800", strokeWidth: 0 }}
            activeDot={{ r: 4, stroke: "#FFB800", strokeWidth: 2, fill: "#00FFFF" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
