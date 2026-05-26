import type { CockpitSystemLite, DashboardCockpitBundle } from "@/lib/cockpit-bundle";
import type { AgentRow, TaskQueueItem, TaskQueueResponse, TaskRow } from "@/lib/hive-types";

/** Compact agent patch from WS ``hive.snapshot`` frames. */
export interface CockpitAgentDelta {
  id: string;
  status: string;
  pollen_points: number;
  performance_score: number;
  current_task_id?: string | null;
  current_task_title?: string | null;
  hive_tier?: string | null;
}

/** Task queue strip from WS — counts plus recently updated rows. */
export type TaskQueueWsStrip = TaskQueueResponse;

/** Compact Execution Studio pending counts pushed over WS. */
export interface OperatorPendingWsStrip {
  revision: number;
  count: number;
  browser_pending: number;
  external_pending: number;
  codebase_pending: number;
  review_pending?: number;
  pending_alert?: {
    fingerprint: string;
    type: "browser" | "external";
    message: string;
    supervisor_session_id?: string;
  };
}

/** Live pulse payload from ``GET /ws/live`` (extends legacy counter-only shape). */
export interface HiveLivePulsePayload {
  type?: string;
  revision?: number;
  agents?: number;
  tasks_pending?: number;
  pollen_points_total?: number;
  system_status?: CockpitSystemLite;
  agent_deltas?: CockpitAgentDelta[];
  recent_tasks?: TaskRow[];
  task_queue_strip?: TaskQueueWsStrip;
  operator_pending_strip?: OperatorPendingWsStrip;
}

function bumpStatusCount(counts: Record<string, number>, status: string, delta: number): void {
  const next = Math.max(0, (counts[status] ?? 0) + delta);
  if (next === 0) {
    delete counts[status];
  } else {
    counts[status] = next;
  }
}

function bumpTierCount(counts: Record<string, number>, tier: string | null | undefined, delta: number): void {
  const key = tier?.trim() || "unknown";
  bumpStatusCount(counts, key, delta);
}

/** Whether a full ``GET /dashboard/cockpit`` refetch is required after this pulse. */
export function shouldRevalidateCockpitAfterPulse(
  bundle: DashboardCockpitBundle | undefined,
  pulse: HiveLivePulsePayload,
): boolean {
  if (!bundle) {
    return true;
  }

  const rosterTotal = pulse.system_status?.agents_total ?? pulse.agents;
  if (typeof rosterTotal === "number" && rosterTotal !== bundle.summary.agents.total) {
    return true;
  }

  if (pulse.recent_tasks?.length || pulse.task_queue_strip) {
    if (!pulse.agent_deltas?.length) {
      return false;
    }
  }

  if (!pulse.agent_deltas?.length) {
    return !pulse.system_status;
  }

  const known = new Set(bundle.agents.map((agent) => agent.id));
  return pulse.agent_deltas.some((delta) => !known.has(delta.id));
}

/** Merge WS pulse into cached cockpit bundle without a network round-trip. */
export function applyCockpitWsDelta(
  bundle: DashboardCockpitBundle,
  pulse: HiveLivePulsePayload,
): DashboardCockpitBundle {
  const revision = typeof pulse.revision === "number" ? pulse.revision : bundle.revision;
  const systemStatus = pulse.system_status ?? bundle.system_status;
  const agentsTotal = systemStatus.agents_total;
  const tasksPending = systemStatus.tasks_pending;

  let nextAgents = bundle.agents;
  const byStatus = { ...bundle.summary.agents.by_status };
  const byHiveTier = { ...bundle.summary.agents.by_hive_tier };

  if (pulse.agent_deltas?.length) {
    const deltaById = new Map(pulse.agent_deltas.map((row) => [row.id, row]));
    nextAgents = bundle.agents.map((agent) => {
      const delta = deltaById.get(agent.id);
      if (!delta) {
        return agent;
      }

      if (agent.status !== delta.status) {
        bumpStatusCount(byStatus, agent.status, -1);
        bumpStatusCount(byStatus, delta.status, 1);
      }

      const nextTier = delta.hive_tier ?? agent.hive_tier ?? null;
      if ((agent.hive_tier ?? null) !== nextTier) {
        bumpTierCount(byHiveTier, agent.hive_tier, -1);
        bumpTierCount(byHiveTier, nextTier, 1);
      }

      return {
        ...agent,
        status: delta.status as AgentRow["status"],
        pollen_points: delta.pollen_points,
        performance_score: delta.performance_score,
        current_task_id: delta.current_task_id ?? null,
        current_task_title: delta.current_task_title ?? null,
        hive_tier: nextTier,
      };
    });
  }

  return {
    ...bundle,
    revision,
    generated_at: new Date().toISOString(),
    agents: nextAgents,
    recent_tasks: pulse.recent_tasks ?? bundle.recent_tasks,
    system_status: systemStatus,
    summary: {
      ...bundle.summary,
      generated_at: new Date().toISOString(),
      agents: {
        ...bundle.summary.agents,
        total: agentsTotal,
        by_status: byStatus,
        by_hive_tier: byHiveTier,
      },
      tasks: {
        pending: tasksPending,
      },
    },
  };
}

function mergeTaskQueueRows(existing: TaskQueueItem[], incoming: TaskQueueItem[]): TaskQueueItem[] {
  const deltaById = new Map(incoming.map((row) => [row.id, row]));
  const merged = existing.map((row) => deltaById.get(row.id) ?? row);

  for (const row of incoming) {
    if (!merged.some((item) => item.id === row.id)) {
      merged.unshift(row);
    }
  }

  return merged
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
    .slice(0, 120);
}

/** Patch task queue widget cache from WS strip without refetching ``/dashboard/task-queue``. */
export function applyTaskQueueWsDelta(
  current: TaskQueueResponse | undefined,
  strip: TaskQueueWsStrip,
): TaskQueueResponse {
  const tasks = mergeTaskQueueRows(current?.tasks ?? [], strip.tasks);

  return {
    generated_at: strip.generated_at,
    running_count: strip.running_count,
    pending_count: strip.pending_count,
    completed_today_count: strip.completed_today_count,
    tasks,
  };
}

/** Whether task queue widget needs a full HTTP refetch after WS strip. */
export function shouldRevalidateTaskQueueAfterPulse(strip: TaskQueueWsStrip): boolean {
  return strip.tasks.length === 0;
}
