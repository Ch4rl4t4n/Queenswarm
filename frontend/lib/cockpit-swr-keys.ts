/** Shared SWR cache keys — dedupe dashboard + page polls within one tab. */

import { COCKPIT_PERF } from "@/lib/cockpit-performance-budget";

export const cockpitSwrKeys = {
  bundle: (agentsLimit: number, tasksLimit: number) =>
    ["cockpit", "bundle", agentsLimit, tasksLimit] as const,
  agentsDashboard: () => ["cockpit", "agents", COCKPIT_PERF.dashboardAgentsLimit] as const,
  agentsFull: () => ["cockpit", "agents", COCKPIT_PERF.fullAgentsLimit] as const,
  recentTasks: () => ["cockpit", "recent-tasks", COCKPIT_PERF.recentTasksLimit] as const,
  systemStatus: () => ["cockpit", "system-status"] as const,
  dashboardSummary: () => ["cockpit", "dashboard-summary"] as const,
  costs30d: () => ["cockpit", "costs-30d"] as const,
  taskQueue: (limit: number) => ["cockpit", "task-queue", limit] as const,
  swarmBoard: () => ["cockpit", "swarm-board"] as const,
} as const;
