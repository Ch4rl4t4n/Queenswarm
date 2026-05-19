"use client";

import useSWR from "swr";

import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";
import { COCKPIT_POLL_SYSTEM_STATUS_MS } from "@/lib/cockpit-poll-profile";

export interface HiveSystemHealth {
  redis_ok: boolean;
  celery_ok: boolean;
  celery_workers_up?: number;
  celery_active_tasks?: number;
  celery_reserved_tasks?: number;
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
      <V4Card className="border-(--qs-red)/35">
        <p className="text-sm text-(--qs-red)">
          System probe failed — retry after logging into the hive proxy.
        </p>
      </V4Card>
    );
  }

  if (!data) {
    return (
      <V4Card className="animate-pulse">
        <p className="text-xs text-(--qs-text-3)">Fetching swarm diagnostics…</p>
      </V4Card>
    );
  }

  const rows: { label: string; ok: boolean }[] = [
    { label: "Redis cache", ok: data.redis_ok },
    { label: "Celery worker", ok: data.celery_ok },
    { label: "Postgres ledger", ok: data.db_ok },
    { label: "LLM provider keys", ok: data.llm_ok },
  ];

  return (
    <V4Card glow>
      <V4CardHeader
        as="h3"
        title="System status"
        description="Live infra snapshot for swarm operators — adaptive polling via cookie JWT."
      />
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {rows.map((row) => (
          <div
            key={row.label}
            className="flex items-center gap-3 rounded-xl border border-(--qs-border) bg-black/35 px-4 py-3"
          >
            <span
              className={`h-2.5 w-2.5 shrink-0 rounded-full ${row.ok ? "bg-(--qs-green) shadow-[0_0_12px_rgb(0_255_136/0.65)]" : "animate-pulse bg-(--qs-red)"}`}
            />
            <div className="flex flex-col">
              <span className={`text-sm ${row.ok ? "text-(--qs-text)" : "text-(--qs-red)"}`}>{row.label}</span>
              <span className="text-[11px] text-(--qs-text-3)">
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
      <p className="mt-4 text-xs text-(--qs-text-3)">
        Celery {data.celery_workers_up ?? 0} workers · active {data.celery_active_tasks ?? 0} · reserved{" "}
        {data.celery_reserved_tasks ?? 0} · LLM slots {data.llm_in_flight}/{data.llm_concurrency_limit} · simulations{" "}
        {data.simulation_in_flight}/{data.simulation_concurrency_limit}
      </p>
      {data.simulation_enabled && (data.simulation_tasks_running > 0 || data.simulation_tasks_pending > 0) ? (
        <div className="mt-4 rounded-xl border border-(--qs-gold)/25 bg-(--qs-gold)/10 p-3 text-xs text-(--qs-gold)">
          Simulations pressure: running {data.simulation_tasks_running}, queued {data.simulation_tasks_pending}.
          {data.simulation_tasks_pending > 2 ? " Queue is high — consider temporary throttle." : ""}
        </div>
      ) : null}
      {data.resource_pressure ? (
        <div className="mt-3 rounded-xl border border-(--qs-red)/30 bg-(--qs-red)/10 p-3 text-xs text-(--qs-red)">
          Host resource pressure detected ({data.resource_pressure_reason || "system_high"}). Reduce concurrent workload before
          launching more simulations.
        </div>
      ) : null}
      {!data.llm_ok ? (
        <div className="mt-5 rounded-xl border border-(--qs-red)/25 bg-(--qs-red)/10 p-4 text-xs text-(--qs-red)">
          LLM routing disabled · add{" "}
          <code className="text-[11px] text-(--qs-cyan)">GROK_API_KEY</code>,{" "}
          <code className="text-[11px] text-(--qs-cyan)">ANTHROPIC_API_KEY</code>, or{" "}
          <code className="text-[11px] text-(--qs-cyan)">OPENAI_API_KEY</code> to{" "}
          <span className="text-(--qs-gold)">.env</span> and recycle <span className="text-(--qs-gold)">celery-worker</span>. Bees still
          serialize tool rails without paid inference.
          <span className="mt-3 block text-[11px] text-(--qs-text-3)">
            Console:{" "}
            <a
              href="https://console.x.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-(--qs-cyan) underline-offset-4 hover:underline"
            >
              https://console.x.ai
            </a>
          </span>
        </div>
      ) : null}
    </V4Card>
  );
}

function MetricChip({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="rounded-lg border border-(--qs-border) bg-black/35 px-3 py-2">
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-(--qs-text-3)">{label}</p>
      <p className="mt-1 text-sm text-(--qs-text)">{value}</p>
    </div>
  );
}
