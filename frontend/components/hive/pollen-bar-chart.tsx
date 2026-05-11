"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface PollenBarDatum {
  label: string;
  pollen: number;
}

interface PollenRankChartProps {
  data: PollenBarDatum[];
}

export function PollenRankChart({ data }: PollenRankChartProps) {
  return (
    <div className="h-72 w-full rounded-2xl border border-cyan/20 bg-black/30 p-4">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="label" tick={{ fill: "#9ca3af", fontSize: 10 }} />
          <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} />
          <Tooltip contentStyle={{ background: "#050510", border: "1px solid #FFB800", borderRadius: 8 }} />
          <Bar dataKey="pollen" fill="#FFB800" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
