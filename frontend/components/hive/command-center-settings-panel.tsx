"use client";

import { ActivityIcon, BellIcon, ContainerIcon, Loader2Icon, ServerIcon } from "lucide-react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useCallback, useState } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import { cn } from "@/lib/utils";

const POLL_MS = 15_000;

const CommandCenterAuditRollupCard = dynamic(
  () =>
    import("@/components/hive/command-center-audit-rollup-card").then((mod) => ({
      default: mod.CommandCenterAuditRollupCard,
    })),
  { ssr: false, loading: () => <div className="min-h-[12rem] animate-pulse rounded-xl bg-white/5" aria-hidden /> },
);

const CommandCenterCodebaseAtlas = dynamic(
  () =>
    import("@/components/hive/command-center-codebase-atlas").then((mod) => ({
      default: mod.CommandCenterCodebaseAtlas,
    })),
  { ssr: false, loading: () => <div className="min-h-[16rem] animate-pulse rounded-xl bg-white/5" aria-hidden /> },
);

interface CommandCenterHost {
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_used_gb: number;
  disk_total_gb: number;
  swap_percent: number;
  resource_pressure: boolean;
  resource_pressure_reason: string;
}

interface CommandCenterDependency {
  key: string;
  label: string;
  category: string;
  ok: boolean;
  latency_ms?: number | null;
  error?: string | null;
  detail?: string | null;
}

interface CommandCenterLlmProvider {
  provider: string;
  label: string;
  role: string;
  route: string;
  configured: boolean;
  source: string;
}

interface CommandCenterIntegration {
  key: string;
  label: string;
  category: string;
  ok: boolean;
  detail: string;
  source: string;
}

interface CommandCenterHiveLoad {
  agents_total: number;
  agents_running: number;
  tasks_running: number;
  tasks_pending: number;
  simulation_tasks_running: number;
  simulation_tasks_pending: number;
  llm_in_flight: number;
  llm_concurrency_limit: number;
  simulation_in_flight: number;
  simulation_concurrency_limit: number;
  simulations_enabled: boolean;
}

interface CommandCenterHostHistoryPoint {
  ts: string;
  cpu: number;
  memory: number;
  disk: number;
}

interface CommandCenterDockerContainer {
  name: string;
  image: string;
  status: string;
}

interface CommandCenterDocker {
  available: boolean;
  running_total: number | null;
  queenswarm_running: number | null;
  containers: CommandCenterDockerContainer[];
}

interface CommandCenterTelemetry {
  rate_limit_blocks_5m: number;
  scaling_events_5m: number;
}

interface CommandCenterSnapshot {
  generated_at: string;
  instance_id: string;
  host: CommandCenterHost;
  dependencies: CommandCenterDependency[];
  llm_providers: CommandCenterLlmProvider[];
  integrations: CommandCenterIntegration[];
  hive_load: CommandCenterHiveLoad;
  docker: CommandCenterDocker;
  host_history: CommandCenterHostHistoryPoint[];
  telemetry: CommandCenterTelemetry;
  summary: {
    dependencies_ok: boolean;
    llm_routes_ok: boolean;
    integrations_ok: boolean;
  };
}

function barTone(percent: number): string {
  if (percent >= 90) return "bg-(--qs-red)";
  if (percent >= 75) return "bg-pollen";
  return "bg-(--qs-green)";
}

function ResourceBar({
  label,
  percent,
  detail,
  history,
  historyField,
}: {
  label: string;
  percent: number;
  detail: string;
  history?: CommandCenterHostHistoryPoint[];
  historyField?: "cpu" | "memory" | "disk";
}) {
  const values =
    history && historyField ? history.map((point) => point[historyField]) : [];
  const max = values.length ? Math.max(...values, 1) : 100;

  return (
    <div className="rounded-xl border border-(--qs-border) bg-black/35 p-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-(--qs-text-3)">{label}</span>
        <span className="text-sm font-medium text-(--qs-text)">{percent.toFixed(1)}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <div className={cn("h-full rounded-full transition-all", barTone(percent))} style={{ width: `${Math.min(100, percent)}%` }} />
      </div>
      {values.length > 1 ? (
        <div
          className="mt-3 flex h-10 items-end gap-px"
          role="img"
          aria-label={`${label} history — last ${values.length} samples`}
        >
          {values.slice(-48).map((value, index) => (
            <div
              key={`${label}-${index}`}
              className={cn("flex-1 rounded-t-sm opacity-80", barTone(value))}
              style={{ height: `${Math.max(8, (value / max) * 100)}%` }}
            />
          ))}
        </div>
      ) : null}
      <p className="mt-2 text-[11px] text-(--qs-text-3)">{detail}</p>
    </div>
  );
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={cn(
        "inline-block h-2.5 w-2.5 rounded-full",
        ok ? "bg-(--qs-green) shadow-[0_0_10px_rgb(0_255_136/0.55)]" : "animate-pulse bg-(--qs-red)",
      )}
      aria-hidden
    />
  );
}

export function CommandCenterSettingsPanel() {
  const { isAdmin, platformMode } = usePlatform();
  const allowed = isAdmin && platformMode === "internal";

  const [snapshot, setSnapshot] = useState<CommandCenterSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notifyBusy, setNotifyBusy] = useState(false);
  const [notifyResult, setNotifyResult] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    try {
      const body = await hiveGet<CommandCenterSnapshot>("operator/command-center");
      setSnapshot(body);
      setError(null);
    } catch (exc) {
      const msg = exc instanceof HiveApiError ? exc.message : "Command center probe failed.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [allowed]);

  useIntervalWhenVisible(() => void load(), allowed ? POLL_MS : null);

  const runNotifyTest = useCallback(async () => {
    setNotifyBusy(true);
    setNotifyResult(null);
    try {
      const body = await hivePostJson<{ message: string; results: Record<string, boolean> }>(
        "operator/command-center/notify-test",
        {},
      );
      setNotifyResult(body.message);
    } catch (exc) {
      const msg = exc instanceof HiveApiError ? exc.message : "Notify test failed.";
      setNotifyResult(msg);
    } finally {
      setNotifyBusy(false);
    }
  }, []);

  if (!allowed) {
    return (
      <V4Card>
        <V4CardHeader title="Command center" description="Dostupné len pre admin v internal tenante." />
      </V4Card>
    );
  }

  const snapshotReady = snapshot != null;

  const {
    host,
    dependencies,
    llm_providers,
    integrations,
    hive_load: loadStats,
    docker = { available: false, running_total: null, queenswarm_running: null, containers: [] },
    host_history = [],
    telemetry = { rate_limit_blocks_5m: 0, scaling_events_5m: 0 },
  } = snapshot ?? {
    host: {
      cpu_percent: 0,
      memory_percent: 0,
      disk_percent: 0,
      memory_used_gb: 0,
      memory_total_gb: 0,
      disk_used_gb: 0,
      disk_total_gb: 0,
      swap_percent: 0,
      resource_pressure: false,
      resource_pressure_reason: "",
    },
    dependencies: [],
    llm_providers: [],
    integrations: [],
    hive_load: {
      agents_total: 0,
      agents_running: 0,
      tasks_running: 0,
      tasks_pending: 0,
      simulation_tasks_running: 0,
      simulation_tasks_pending: 0,
      llm_in_flight: 0,
      llm_concurrency_limit: 0,
      simulation_in_flight: 0,
      simulation_concurrency_limit: 0,
      simulations_enabled: false,
    },
    docker: { available: false, running_total: null, queenswarm_running: null, containers: [] },
    host_history: [],
    telemetry: { rate_limit_blocks_5m: 0, scaling_events_5m: 0 },
  };

  return (
    <div className="space-y-4">
      {!snapshotReady && loading ? (
        <V4Card className="flex min-h-[200px] items-center justify-center">
          <Loader2Icon className="h-6 w-6 animate-spin text-pollen" aria-hidden />
        </V4Card>
      ) : null}

      {!snapshotReady && error ? (
        <V4Card className="border-(--qs-red)/35 p-4">
          <p className="text-sm text-(--qs-red)">{error}</p>
        </V4Card>
      ) : null}

      {snapshotReady && snapshot ? (
        <V4Card className="overflow-hidden p-0">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-(--qs-border) px-4 py-4 md:px-6">
          <V4CardHeader
            as="h2"
            kicker="Admin · ops"
            title="Command center"
            description="Server load, RAM, disk, databázy, queue, and LLM prepojenia — live snapshot."
          />
          <div className="flex flex-wrap items-center gap-2">
            <V4Badge tone={snapshot.summary.dependencies_ok ? "ok" : "err"}>
              {snapshot.summary.dependencies_ok ? "deps ok" : "deps degraded"}
            </V4Badge>
            <V4Badge tone={snapshot.summary.llm_routes_ok ? "ok" : "warn"}>
              {snapshot.summary.llm_routes_ok ? "llm ready" : "llm missing"}
            </V4Badge>
            <HiveRefreshButton onClick={() => void load()} />
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm gap-2"
              disabled={notifyBusy}
              onClick={() => void runNotifyTest()}
            >
              {notifyBusy ? (
                <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <BellIcon className="h-4 w-4" aria-hidden />
              )}
              Test notify
            </button>
          </div>
        </div>

        {notifyResult ? (
          <div className="mx-4 mt-0 rounded-xl border border-cyan/25 bg-cyan/5 px-4 py-2 text-xs text-cyan md:mx-6">
            {notifyResult}
          </div>
        ) : null}

        <div className="grid gap-4 px-4 py-4 md:grid-cols-3 md:px-6">
          <ResourceBar
            label="CPU"
            percent={host.cpu_percent}
            detail={`Instance ${snapshot.instance_id}`}
            history={host_history}
            historyField="cpu"
          />
          <ResourceBar
            label="RAM"
            percent={host.memory_percent}
            detail={`${host.memory_used_gb} / ${host.memory_total_gb} GB · swap ${host.swap_percent.toFixed(1)}%`}
            history={host_history}
            historyField="memory"
          />
          <ResourceBar
            label="Disk"
            percent={host.disk_percent}
            detail={`${host.disk_used_gb} / ${host.disk_total_gb} GB`}
            history={host_history}
            historyField="disk"
          />
        </div>

        {host.resource_pressure ? (
          <div className="mx-4 mb-4 rounded-xl border border-(--qs-red)/30 bg-(--qs-red)/10 px-4 py-3 text-xs text-(--qs-red) md:mx-6">
            Resource pressure: {host.resource_pressure_reason || "high_load"} — zváž throttle simulácií / LLM slotov.
          </div>
        ) : null}

        <div className="grid gap-4 border-t border-(--qs-border)/70 px-4 py-4 md:grid-cols-2 md:px-6">
          <section>
            <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-cyan">
              <ServerIcon className="h-4 w-4" aria-hidden />
              Infra & dependencies
            </h3>
            <div className="space-y-2">
              {dependencies.map((row) => (
                <div
                  key={row.key}
                  className="flex items-center justify-between gap-3 rounded-lg border border-(--qs-border) bg-black/30 px-3 py-2.5"
                >
                  <div className="flex items-center gap-2">
                    <StatusDot ok={row.ok} />
                    <div>
                      <p className="text-sm text-(--qs-text)">{row.label}</p>
                      <p className="text-[10px] text-(--qs-text-3)">
                        {row.detail ??
                          (row.latency_ms != null ? `${row.latency_ms} ms` : row.error ?? row.category)}
                      </p>
                    </div>
                  </div>
                  <V4Badge tone={row.ok ? "ok" : "err"}>{row.ok ? "up" : "down"}</V4Badge>
                </div>
              ))}
            </div>
          </section>

          <section>
            <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-pollen">
              <ActivityIcon className="h-4 w-4" aria-hidden />
              Hive load
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {[
                ["Agents", `${loadStats.agents_running}/${loadStats.agents_total} running`],
                ["Tasks", `${loadStats.tasks_running} run · ${loadStats.tasks_pending} pending`],
                ["LLM slots", `${loadStats.llm_in_flight}/${loadStats.llm_concurrency_limit}`],
                ["Simulations", `${loadStats.simulation_in_flight}/${loadStats.simulation_concurrency_limit}`],
              ].map(([label, value]) => (
                <div key={label} className="rounded-lg border border-(--qs-border) bg-black/30 px-3 py-2">
                  <p className="font-mono text-[10px] uppercase tracking-wide text-(--qs-text-3)">{label}</p>
                  <p className="mt-1 text-sm text-(--qs-text)">{value}</p>
                </div>
              ))}
            </div>
            {loadStats.simulations_enabled &&
            (loadStats.simulation_tasks_running > 0 || loadStats.simulation_tasks_pending > 0) ? (
              <p className="mt-3 text-xs text-pollen">
                Simulation queue: {loadStats.simulation_tasks_running} running, {loadStats.simulation_tasks_pending}{" "}
                pending
              </p>
            ) : null}
            <div className="mt-3 grid grid-cols-2 gap-2">
              <div className="rounded-lg border border-(--qs-border) bg-black/30 px-3 py-2">
                <p className="font-mono text-[10px] uppercase tracking-wide text-(--qs-text-3)">Rate limits (5m)</p>
                <p className="mt-1 text-sm text-(--qs-text)">{telemetry.rate_limit_blocks_5m} blocks</p>
              </div>
              <div className="rounded-lg border border-(--qs-border) bg-black/30 px-3 py-2">
                <p className="font-mono text-[10px] uppercase tracking-wide text-(--qs-text-3)">Scaling (5m)</p>
                <p className="mt-1 text-sm text-(--qs-text)">{telemetry.scaling_events_5m} events</p>
              </div>
            </div>
          </section>
        </div>

        <div className="border-t border-(--qs-border)/70 px-4 py-4 md:px-6">
          <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-cyan">
            <ContainerIcon className="h-4 w-4" aria-hidden />
            Docker
            {docker.available && docker.queenswarm_running != null ? (
              <span className="font-normal normal-case text-(--qs-text-3)">
                · {docker.queenswarm_running} queenswarm / {docker.running_total ?? "?"} total
              </span>
            ) : null}
          </h3>
          {!docker.available ? (
            <p className="text-xs text-(--qs-text-3)">Docker socket unavailable — running on bare metal or restricted env.</p>
          ) : docker.containers.length === 0 ? (
            <p className="text-xs text-(--qs-text-3)">No running queenswarm containers detected.</p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {docker.containers.map((container) => (
                <div
                  key={container.name}
                  className="rounded-lg border border-(--qs-border) bg-black/30 px-3 py-2.5"
                >
                  <p className="truncate font-mono text-xs text-(--qs-text)">{container.name}</p>
                  <p className="mt-1 truncate text-[10px] text-(--qs-text-3)">{container.image}</p>
                  <V4Badge tone="ok" className="mt-2">
                    {container.status}
                  </V4Badge>
                </div>
              ))}
            </div>
          )}
        </div>
      </V4Card>
      ) : null}

      <CommandCenterAuditRollupCard enabled={allowed} />

      <CommandCenterCodebaseAtlas enabled={allowed} />

      {snapshotReady && snapshot ? (
        <>
      <V4Card className="overflow-hidden p-0">
        <div className="border-b border-(--qs-border) px-4 py-4 md:px-6">
          <V4CardHeader as="h3" title="LLM & API routes" description="Credentials, ktoré celá aplikácia využíva (env + vault)." />
        </div>
        <div className="overflow-x-auto hive-scrollbar">
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-(--qs-border) bg-black/25 text-left text-[10px] uppercase tracking-wide text-(--qs-text-3)">
                <th className="px-4 py-2 md:px-6">Provider</th>
                <th className="px-3 py-2">Role</th>
                <th className="px-3 py-2">Route</th>
                <th className="px-3 py-2">Source</th>
                <th className="px-4 py-2 md:px-6">Status</th>
              </tr>
            </thead>
            <tbody>
              {llm_providers.map((row) => (
                <tr key={row.provider} className="border-b border-(--qs-border)/60">
                  <td className="px-4 py-2.5 font-medium text-(--qs-text) md:px-6">{row.label}</td>
                  <td className="px-3 py-2.5 text-(--qs-text-2)">{row.role}</td>
                  <td className="px-3 py-2.5 font-mono text-xs text-cyan">{row.route}</td>
                  <td className="px-3 py-2.5 capitalize text-(--qs-text-3)">{row.source}</td>
                  <td className="px-4 py-2.5 md:px-6">
                    <V4Badge tone={row.configured ? "ok" : "warn"}>{row.configured ? "configured" : "missing"}</V4Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="border-t border-(--qs-border)/70 px-4 py-3 text-xs text-(--qs-text-3) md:px-6">
          Upraviť kľúče:{" "}
          <Link href="/settings/llm-keys" className="text-cyan hover:underline">
            Settings → AI · LLM & Voice
          </Link>
        </div>
      </V4Card>

      <V4Card className="overflow-hidden p-0">
        <div className="px-4 py-4 md:px-6">
          <V4CardHeader as="h3" title="Integrations" description="Voice and observability flags." />
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {integrations.map((row) => (
              <div
                key={row.key}
                className="flex items-start justify-between gap-2 rounded-lg border border-(--qs-border) bg-black/30 px-3 py-2.5"
              >
                <div>
                  <p className="text-sm text-(--qs-text)">{row.label}</p>
                  <p className="text-[10px] text-(--qs-text-3)">{row.detail}</p>
                </div>
                <V4Badge tone={row.ok ? "ok" : "info"}>{row.ok ? "ok" : "off"}</V4Badge>
              </div>
            ))}
          </div>
          <p className="mt-4 font-mono text-[10px] text-(--qs-text-3)">
            Last sync: {new Date(snapshot.generated_at).toLocaleString()} · poll {POLL_MS / 1000}s · history{" "}
            {host_history.length} samples
          </p>
        </div>
      </V4Card>
        </>
      ) : null}
    </div>
  );
}
