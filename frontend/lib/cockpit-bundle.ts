import type { AgentRow, DashboardSummary, SystemStatusPayload, TaskRow } from "@/lib/hive-types";

/** Lite system gauges bundled with cockpit telemetry (no Celery/host probes). */
export interface CockpitSystemLite {
  agents_total: number;
  agents_running: number;
  tasks_running: number;
  tasks_pending: number;
  llm_grok: boolean;
  llm_anthropic: boolean;
}

/** Single-shot dashboard hydration from GET /dashboard/cockpit. */
export interface DashboardCockpitBundle {
  generated_at: string;
  revision: number;
  agents: AgentRow[];
  recent_tasks: TaskRow[];
  summary: DashboardSummary;
  system_status: CockpitSystemLite;
}

/** Map lite gauges into chrome-compatible system status (unknown probes default safe). */
export function mapCockpitSystemLiteToStatus(lite: CockpitSystemLite): SystemStatusPayload {
  return {
    redis_ok: true,
    celery_ok: true,
    db_ok: true,
    llm_ok: lite.llm_grok || lite.llm_anthropic,
    llm_grok: lite.llm_grok,
    llm_anthropic: lite.llm_anthropic,
    agents_total: lite.agents_total,
    agents_running: lite.agents_running,
    tasks_running: lite.tasks_running,
    tasks_pending: lite.tasks_pending,
    host_cpu_percent: 0,
    host_memory_percent: 0,
    host_disk_percent: 0,
    llm_concurrency_limit: 0,
    llm_in_flight: 0,
    simulation_concurrency_limit: 0,
    simulation_in_flight: 0,
    simulation_enabled: false,
    simulation_tasks_running: 0,
    simulation_tasks_pending: 0,
    resource_pressure: false,
    resource_pressure_reason: "",
  };
}
