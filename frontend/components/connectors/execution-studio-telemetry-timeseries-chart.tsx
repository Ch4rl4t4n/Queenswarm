"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface ActivityTimeSeriesDatum {
  bucket: string;
  runs: number;
  blocks: number;
}

interface ExecutionStudioTelemetryTimeseriesChartProps {
  data: ActivityTimeSeriesDatum[];
}

function formatBucketLabel(bucket: string): string {
  if (bucket.length >= 13) {
    return bucket.slice(11, 13) + ":00";
  }
  return bucket;
}

/** Hourly tool runs vs cost blocks over recent activity window. */
export function ExecutionStudioTelemetryTimeseriesChart({
  data,
}: ExecutionStudioTelemetryTimeseriesChartProps) {
  if (data.length === 0) {
    return null;
  }

  const chartData = data.map((row) => ({
    ...row,
    label: formatBucketLabel(row.bucket),
  }));

  return (
    <div className="h-56 w-full rounded-xl border border-[color:var(--qs-border-2)]/15 bg-black/35 p-3">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="studioRunsGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00FFFF" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#00FFFF" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="studioBlocksGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#FF00AA" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#FF00AA" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 6" stroke="rgb(0 255 255 / 0.08)" />
          <XAxis dataKey="label" tick={{ fill: "#71717a", fontSize: 10 }} axisLine={{ stroke: "rgb(0 255 255 / 0.12)" }} />
          <YAxis allowDecimals={false} tick={{ fill: "#71717a", fontSize: 10 }} axisLine={{ stroke: "rgb(0 255 255 / 0.12)" }} />
          <Tooltip
            contentStyle={{
              background: "#121214",
              border: "1px solid rgb(0 255 255 / 0.35)",
              borderRadius: "10px",
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "12px",
            }}
            labelFormatter={(_label, payload) => {
              const row = payload?.[0]?.payload as ActivityTimeSeriesDatum | undefined;
              return row?.bucket ?? _label;
            }}
          />
          <Legend wrapperStyle={{ fontSize: "11px", color: "#a1a1aa" }} />
          <Area type="monotone" dataKey="runs" name="Runs" stroke="#00FFFF" fill="url(#studioRunsGrad)" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Area type="monotone" dataKey="blocks" name="Blocked" stroke="#FF00AA" fill="url(#studioBlocksGrad)" strokeWidth={2} dot={false} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
