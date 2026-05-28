/**
 * Execution lane routing SSOT — Tasks hub, Workflows DAG, Async jobs (Whole-App UI Reorder Phase 18).
 *
 * More-menu routes (`/workflows`, `/jobs`) stay reachable from the Tasks hub and each other.
 */

export const TASKS_HUB_PATH = "/tasks";
export const WORKFLOWS_PATH = "/workflows";
export const JOBS_PATH = "/jobs";
export const FORAGERS_PATH = "/foragers";
export const AGENTS_HUB_PATH = "/agents";
export const KNOWLEDGE_HIVEMIND_HREF = "/knowledge#hivemind";

/** Operator-facing cross-link labels — keep UI + E2E in sync. */
export const EXECUTION_LANE_CROSS_LINK_LABELS = {
  toTasksHub: "Tasks hub",
  toWorkflows: "Workflows",
  toAsyncJobs: "Async jobs",
  toForagers: "Foragers",
  toAgentsHub: "Agents hub",
  toHiveMind: "HiveMind",
} as const;

/** Tasks hub lane cards — SSOT for `/tasks` discovery strip. */
export const TASKS_HUB_LANE_LINKS = [
  { href: "/tasks/new", label: "New task" },
  { href: WORKFLOWS_PATH, label: EXECUTION_LANE_CROSS_LINK_LABELS.toWorkflows },
  { href: JOBS_PATH, label: "Jobs" },
  { href: AGENTS_HUB_PATH, label: "Routines" },
] as const;
