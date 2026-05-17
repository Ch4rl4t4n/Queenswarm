"use client";

import type { ReactNode } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import useSWR from "swr";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { MonitoringSkeleton } from "@/components/monitoring/monitoring-skeleton";
import { hiveGet } from "@/lib/api";
import { COCKPIT_POLL_SYSTEM_STATUS_MS } from "@/lib/cockpit-poll-profile";
import type { MonitoringSnapshot } from "@/lib/monitoring-types";
import { cn } from "@/lib/utils";

const SWR_KEY = "operator/monitoring/snapshot";

function formatBytes(n: number): string {
  if (n < 1024) {
    return `${n} B`;
  }
  const kb = n / 1024;
  if (kb < 1024) {
    return `${kb.toFixed(1)} KiB`;
  }
  const mb = kb / 1024;
  if (mb < 1024) {
    return `${mb.toFixed(1)} MiB`;
  }
  return `${(mb / 1024).toFixed(2)} GiB`;
}

function formatUsd(n: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 }).format(n);
}

interface SamplePoint {
  t: string;
  cpu: number;
  ram: number;
  disk: number;
  swap: number;
}

const MAX_SAMPLES = 48;

export function MonitoringDashboard() {
  const [history, setHistory] = useState<SamplePoint[]>([]);
  const lastTs = useRef<string | null>(null);

  const { data, error, isLoading, isValidating } = useSWR<MonitoringSnapshot>(
    SWR_KEY,
    () => hiveGet<MonitoringSnapshot>("operator/monitoring/snapshot"),
    {
      refreshInterval: COCKPIT_POLL_SYSTEM_STATUS_MS,
      revalidateOnFocus: true,
      dedupingInterval: 5_000,
      focusThrottleInterval: COCKPIT_POLL_SYSTEM_STATUS_MS,
    },
  );

  const appendHistory = useCallback(
    (snap: MonitoringSnapshot) => {
      if (snap.ts === lastTs.current) {
        return;
      }
      lastTs.current = snap.ts;
      const label = new Date(snap.ts).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      setHistory((prev) => {
        const next: SamplePoint[] = [
          ...prev,
          {
            t: label,
            cpu: snap.host.cpu_percent,
            ram: snap.host.memory_percent,
            disk: snap.host.disk_percent,
            swap: snap.host.swap_percent,
          },
        ];
        return next.slice(-MAX_SAMPLES);
      });
    },
    [],
  );

  useEffect(() => {
    if (data) {
      appendHistory(data);
    }
  }, [data, appendHistory]);

  if (error) {
    return (
      <div className="rounded-2xl border border-danger/30 bg-danger/[0.06] p-6 font-[family-name:var(--font-poppins)] text-sm text-danger">
        Monitoring feed unavailable · this page requires admin role + enterprise subscription + enterprise monitoring flag.
      </div>
    );
  }

  if (isLoading && !data) {
    return <MonitoringSkeleton />;
  }

  if (!data) {
    return null;
  }

  const costHourly = data.costs.hourly_usd.map((row) => ({
    label: new Date(row.bucket).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }),
    spend: row.spend_usd,
  }));

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
          Live · {isValidating ? "refreshing…" : "idle"} · {data.collection_ms.toFixed(0)} ms
        </p>
        <p className="font-mono text-[10px] text-cyan/60">{new Date(data.ts).toLocaleString()}</p>
      </div>
      {data.alerts.length > 0 ? (
        <section className="grid gap-3">
          {data.alerts.map((alert) => (
            <div
              key={`${alert.code}-${alert.message}`}
              className={`rounded-xl border px-4 py-3 text-sm ${
                alert.severity === "critical"
                  ? "border-danger/35 bg-danger/10 text-danger"
                  : "border-amber-300/30 bg-amber-300/10 text-amber-200"
              }`}
            >
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] opacity-80">{alert.code}</p>
              <p className="mt-1 font-[family-name:var(--font-poppins)]">{alert.message}</p>
            </div>
          ))}
        </section>
      ) : null}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="CPU" value={`${data.host.cpu_percent.toFixed(1)}%`} accent="text-data" />
        <MetricTile label="RAM" value={`${data.host.memory_percent.toFixed(1)}%`} sub={formatBytes(data.host.memory_used_bytes)} accent="text-pollen" />
        <MetricTile label="Disk /" value={`${data.host.disk_percent.toFixed(1)}%`} sub={formatBytes(data.host.disk_used_bytes)} accent="text-success" />
        <MetricTile label="Swap" value={`${data.host.swap_percent.toFixed(1)}%`} sub={formatBytes(data.host.swap_used_bytes)} accent="text-alert" />
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="CPU & RAM (session window)">
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={history} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="cpuFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00FFFF" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#00FFFF" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="ramFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#FFB800" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#FFB800" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#252a55" />
              <XAxis dataKey="t" tick={{ fill: "#6b6b8a", fontSize: 10 }} interval="preserveStartEnd" />
              <YAxis domain={[0, 100]} tick={{ fill: "#6b6b8a", fontSize: 10 }} width={32} />
              <Tooltip
                contentStyle={{ background: "#0f0f16", border: "1px solid #252a55", borderRadius: 12 }}
                labelStyle={{ color: "#fafafa" }}
              />
              <Area type="monotone" dataKey="cpu" name="CPU %" stroke="#00FFFF" fill="url(#cpuFill)" strokeWidth={2} dot={false} />
              <Area type="monotone" dataKey="ram" name="RAM %" stroke="#FFB800" fill="url(#ramFill)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Disk & swap %">
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={history} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#252a55" />
              <XAxis dataKey="t" tick={{ fill: "#6b6b8a", fontSize: 10 }} interval="preserveStartEnd" />
              <YAxis domain={[0, 100]} tick={{ fill: "#6b6b8a", fontSize: 10 }} width={32} />
              <Tooltip
                contentStyle={{ background: "#0f0f16", border: "1px solid #252a55", borderRadius: 12 }}
                labelStyle={{ color: "#fafafa" }}
              />
              <Area type="monotone" dataKey="disk" name="Disk %" stroke="#00FF88" fill="#00FF8822" strokeWidth={2} dot={false} />
              <Area type="monotone" dataKey="swap" name="Swap %" stroke="#FF00AA" fill="#FF00AA22" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-cyan/[0.12] bg-hive-card/90 p-5 lg:col-span-1">
          <h3 className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#fafafa]">Hive load</h3>
          <ul className="mt-4 space-y-3 font-[family-name:var(--font-poppins)] text-sm text-zinc-300">
            <li className="flex justify-between gap-2">
              <span>Active agents</span>
              <span className="tabular-nums text-pollen">{data.hive.agents_active}</span>
            </li>
            <li className="flex justify-between gap-2">
              <span>Total agents</span>
              <span className="tabular-nums text-[#fafafa]">{data.hive.agents_total}</span>
            </li>
            <li className="flex justify-between gap-2">
              <span>Active tasks</span>
              <span className="tabular-nums text-data">{data.hive.tasks_active}</span>
            </li>
            <li className="flex justify-between gap-2">
              <span>External projects</span>
              <span className="tabular-nums text-success">{data.hive.external_projects}</span>
            </li>
          </ul>
        </div>

        <div className="rounded-2xl border border-cyan/[0.12] bg-hive-card/90 p-5 lg:col-span-1">
          <h3 className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#fafafa]">Docker</h3>
          <p className="mt-4 font-[family-name:var(--font-poppins)] text-3xl tabular-nums text-pollen">
            {data.docker.unavailable ? "—" : data.docker.running_containers}
          </p>
          <p className="mt-2 font-[family-name:var(--font-poppins)] text-xs text-zinc-500">
            {data.docker.unavailable
              ? "Socket not mounted — optional /var/run/docker.sock for live container counts."
              : "Running containers visible to the API service."}
          </p>
        </div>

        <div className="rounded-2xl border border-cyan/[0.12] bg-hive-card/90 p-5 lg:col-span-1">
          <h3 className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#fafafa]">LLM · 24h</h3>
          <p className="mt-4 font-[family-name:var(--font-poppins)] text-3xl text-pollen">{formatUsd(data.costs.usd_24h)}</p>
          <p className="mt-2 font-[family-name:var(--font-poppins)] text-xs text-zinc-500">Summed from cost_records window.</p>
        </div>
        <div className="rounded-2xl border border-cyan/[0.12] bg-hive-card/90 p-5 lg:col-span-1">
          <h3 className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#fafafa]">Critical path</h3>
          <p className="mt-4 font-[family-name:var(--font-poppins)] text-3xl text-danger">
            {data.critical_path.supervisor_failures_24h}
          </p>
          <p className="mt-2 font-[family-name:var(--font-poppins)] text-xs text-zinc-500">
            Supervisor failures observed in last 24h.
          </p>
          <p className="mt-2 font-[family-name:var(--font-poppins)] text-xs text-zinc-500">
            Rate-limit blocks (5m): {data.critical_path.rate_limit_blocks_5m ?? 0}
          </p>
          <p className="mt-1 font-[family-name:var(--font-poppins)] text-xs text-zinc-500">
            Scaling events (5m): {data.critical_path.scaling_events_5m ?? 0}
          </p>
        </div>
      </section>

      {data.enterprise ? (
        <section className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-cyan/[0.12] bg-hive-card/90 p-5">
            <h3 className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#fafafa]">
              Enterprise telemetry
            </h3>
            <ul className="mt-4 space-y-2 font-[family-name:var(--font-poppins)] text-sm text-zinc-300">
              <li className="flex justify-between">
                <span>Tenant tier</span>
                <span className="text-pollen">{data.enterprise.tier}</span>
              </li>
              <li className="flex justify-between">
                <span>Tenant id</span>
                <span className="font-mono text-xs text-zinc-400">{data.enterprise.tenant_id ?? "n/a"}</span>
              </li>
              <li className="flex justify-between">
                <span>OpenTelemetry ready</span>
                <span className={data.enterprise.opentelemetry_ready ? "text-success" : "text-zinc-500"}>
                  {data.enterprise.opentelemetry_ready ? "enabled" : "disabled"}
                </span>
              </li>
              <li className="flex justify-between">
                <span>OTLP endpoint</span>
                <span className={data.enterprise.otlp_endpoint ? "text-success" : "text-zinc-500"}>
                  {data.enterprise.otlp_endpoint ? "configured" : "not configured"}
                </span>
              </li>
            </ul>
          </div>
          <div className="rounded-2xl border border-cyan/[0.12] bg-hive-card/90 p-5">
            <h3 className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#fafafa]">
              Top operator load (24h)
            </h3>
            <div className="mt-4 space-y-2">
              {data.enterprise.top_users_24h.length ? (
                data.enterprise.top_users_24h.slice(0, 8).map((row) => (
                  <div key={row.subject} className="flex items-center justify-between rounded-lg border border-cyan/[0.08] px-3 py-2 text-xs">
                    <span className="font-mono text-zinc-400">{row.subject}</span>
                    <span className="text-zinc-300">sessions {row.sessions}</span>
                    <span className={row.failures > 0 ? "text-danger" : "text-success"}>failures {row.failures}</span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-zinc-500">No user-level activity in the current window.</p>
              )}
            </div>
          </div>
        </section>
      ) : null}

      <ChartCard title="Spend by hour (24h)">
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={costHourly} margin={{ top: 8, right: 8, left: 0, bottom: 32 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#252a55" />
              <XAxis dataKey="label" tick={{ fill: "#6b6b8a", fontSize: 9 }} interval="preserveStartEnd" angle={-35} textAnchor="end" height={48} />
              <YAxis tick={{ fill: "#6b6b8a", fontSize: 10 }} width={44} tickFormatter={(v) => `$${v}`} />
              <Tooltip
                cursor={{ fill: "rgba(0,255,255,0.06)" }}
                contentStyle={{ background: "#0f0f16", border: "1px solid #252a55", borderRadius: 12 }}
                formatter={(value: number) => [formatUsd(value), "Spend"]}
              />
              <Bar dataKey="spend" fill="#FFB800" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>
    </div>
  );
}

function MetricTile({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent: string;
}) {
  return (
    <article className="rounded-2xl border border-cyan/[0.1] bg-hive-card/90 p-4 shadow-[inset_0_0_0_1px_rgb(0_255_255/0.06)]">
      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-500">{label}</p>
      <p className={cn("mt-2 font-[family-name:var(--font-poppins)] text-2xl tabular-nums", accent)}>{value}</p>
      {sub ? <p className="mt-1 font-mono text-[11px] text-zinc-500">{sub}</p> : null}
    </article>
  );
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-cyan/[0.12] bg-hive-card/90 p-4">
      <h3 className="mb-2 font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#fafafa]">{title}</h3>
      {children}
    </div>
  );
}
