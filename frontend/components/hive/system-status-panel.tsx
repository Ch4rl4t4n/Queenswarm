"use client";

import useSWR from "swr";

import { hiveGet } from "@/lib/api";
import { COCKPIT_POLL_SYSTEM_STATUS_MS } from "@/lib/cockpit-poll-profile";

export interface HiveSystemHealth {
  redis_ok: boolean;
  celery_ok: boolean;
  db_ok: boolean;
  llm_ok: boolean;
  host_cpu_percent: number;
  host_memory_percent: number;
  host_disk_percent: number;
  llm_concurrency_limit: number;
  llm_in_flight: number;
  simulation_concurrency_limit: number;
  simulation_in_flight: number;
  simulation_enabled: boolean;
  simulation_tasks_running: number;
  simulation_tasks_pending: number;
  resource_pressure: boolean;
  resource_pressure_reason: string;
}

export function SystemStatusPanel(): JSX.Element {
  const { data, error } = useSWR<HiveSystemHealth>("phase-k/system-status", () => hiveGet<HiveSystemHealth>("system/status"), {
    refreshInterval: COCKPIT_POLL_SYSTEM_STATUS_MS,
    revalidateOnFocus: true,
  });

  if (error) {
    return (
      <section className="mt-8 rounded-2xl border border-danger/35 bg-black/40 p-5">
        <p className="font-[family-name:var(--font-poppins)] text-sm text-danger">
          System probe failed — retry after logging into the hive proxy.
        </p>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="mt-8 animate-pulse rounded-2xl border border-cyan/[0.08] bg-hive-card/80 p-5">
        <p className="font-[family-name:var(--font-poppins)] text-xs text-muted-foreground">Fetching swarm diagnostics…</p>
      </section>
    );
  }

  const rows: { label: string; ok: boolean }[] = [
    { label: "Redis cache", ok: data.redis_ok },
    { label: "Celery worker", ok: data.celery_ok },
    { label: "Postgres ledger", ok: data.db_ok },
    { label: "LLM provider keys", ok: data.llm_ok },
  ];

  return (
    <section className="mt-10 rounded-[22px] qs-rim bg-hive-card/95 p-6 shadow-[inset_0_0_0_1px_rgb(255_184_0/0.08)]">
      <h3 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-pollen">
        🔧 System status
      </h3>
      <p className="mt-1 font-[family-name:var(--font-poppins)] text-sm text-muted-foreground">
        Live infra snapshot for swarm operators — adaptive polling via cookie JWT.
      </p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center gap-3 rounded-xl border border-cyan/[0.08] bg-black/35 px-4 py-3">
            <span
              className={`h-2.5 w-2.5 shrink-0 rounded-full ${row.ok ? "bg-success shadow-[0_0_12px_rgb(0_255_136/0.65)]" : "animate-pulse bg-danger"}`}
            />
            <div className="flex flex-col">
              <span className={`text-sm ${row.ok ? "text-[#fafafa]" : "text-danger"} font-[family-name:var(--font-poppins)]`}>
                {row.label}
              </span>
              <span className="font-[family-name:var(--font-poppins)] text-[11px] text-zinc-500">
                {row.ok ? "nominal · rapid loop draining" : "check docker logs / celery queue"}
              </span>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <MetricChip label="CPU" value={`${data.host_cpu_percent.toFixed(1)}%`} />
        <MetricChip label="RAM" value={`${data.host_memory_percent.toFixed(1)}%`} />
        <MetricChip label="Disk" value={`${data.host_disk_percent.toFixed(1)}%`} />
      </div>
      <p className="mt-4 font-[family-name:var(--font-poppins)] text-xs text-zinc-400">
        LLM slots {data.llm_in_flight}/{data.llm_concurrency_limit} · simulations {data.simulation_in_flight}/
        {data.simulation_concurrency_limit}
      </p>
      {data.simulation_enabled && (data.simulation_tasks_running > 0 || data.simulation_tasks_pending > 0) ? (
        <div className="mt-4 rounded-xl border border-amber-300/25 bg-amber-300/10 p-3 text-xs text-amber-200">
          Simulations pressure: running {data.simulation_tasks_running}, queued {data.simulation_tasks_pending}.
          {data.simulation_tasks_pending > 2 ? " Queue is high — consider temporary throttle." : ""}
        </div>
      ) : null}
      {data.resource_pressure ? (
        <div className="mt-3 rounded-xl border border-danger/30 bg-danger/10 p-3 text-xs text-danger">
          Host resource pressure detected ({data.resource_pressure_reason || "system_high"}). Reduce concurrent workload before
          launching more simulations.
        </div>
      ) : null}
      {!data.llm_ok ? (
        <div className="mt-5 rounded-xl border border-danger/25 bg-danger/10 p-4 font-[family-name:var(--font-poppins)] text-xs text-danger">
          LLM routing disabled · add{" "}
          <code className="text-[11px] text-data">GROK_API_KEY</code>,{" "}
          <code className="text-[11px] text-data">ANTHROPIC_API_KEY</code>, or{" "}
          <code className="text-[11px] text-data">OPENAI_API_KEY</code>{" "}
          to <span className="text-pollen">.env</span> and recycle <span className="text-pollen">celery-worker</span>. Bees still serialize tool
          rails without paid inference.
          <span className="mt-3 block font-[family-name:var(--font-poppins)] text-[11px] text-muted-foreground">
            Console:{" "}
            <a href="https://console.x.ai" target="_blank" rel="noopener noreferrer" className="text-data underline-offset-4 hover:underline">
              https://console.x.ai
            </a>
          </span>
        </div>
      ) : null}
    </section>
  );
}

function MetricChip({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="rounded-lg border border-cyan/[0.12] bg-black/35 px-3 py-2">
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-zinc-500">{label}</p>
      <p className="mt-1 font-[family-name:var(--font-poppins)] text-sm text-[#fafafa]">{value}</p>
    </div>
  );
}
