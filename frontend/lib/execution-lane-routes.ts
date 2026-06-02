/**
 * Execution lane routing SSOT — Tasks hub, Workflows DAG, Async jobs (Whole-App UI Reorder Phase 18).
 *
 * More-menu routes (`/workflows`, `/jobs`) stay reachable from the Tasks hub and each other.
 */

import { ROUTINES_CROSS_LINK_LABELS, ROUTINES_PATH } from "@/lib/routines-routes";

export { ROUTINES_CROSS_LINK_LABELS, ROUTINES_PATH };

export const TASKS_HUB_PATH = "/tasks";
export const WORKFLOWS_PATH = "/workflows";
export const JOBS_PATH = "/jobs";
export const FORAGERS_PATH = "/foragers";
export const AGENTS_HUB_PATH = "/agents";
export const KNOWLEDGE_HIVEMIND_HREF = "/knowledge#hivemind";

/** HiveMind explorer deep-link filtered to one forager's ingested knowledge. */
export function foragerKnowledgeHref(params: { foragerId: string; searchQuery?: string }): string {
  const q = new URLSearchParams();
  q.set("forager", params.foragerId.trim());
  const label = params.searchQuery?.trim();
  if (label) {
    q.set("q", label);
  }
  return `/knowledge?${q.toString()}#explorer`;
}

/** Operator-facing cross-link labels — keep UI + E2E in sync. */
export const EXECUTION_LANE_CROSS_LINK_LABELS = {
  toTasksHub: "Tasks hub",
  toWorkflows: "Workflows",
  toAsyncJobs: "Jobs",
  toForagers: "Foragers",
  toAgentsHub: "Agents hub",
  toHiveMind: "HiveMind",
} as const;

/** Tasks hub lane cards — SSOT for `/tasks` discovery strip. */
export const TASKS_HUB_LANE_LINKS = [
  { href: "/tasks/new", label: "New task" },
  { href: WORKFLOWS_PATH, label: EXECUTION_LANE_CROSS_LINK_LABELS.toWorkflows },
  { href: JOBS_PATH, label: EXECUTION_LANE_CROSS_LINK_LABELS.toAsyncJobs },
  { href: ROUTINES_PATH, label: "Routines" },
] as const;
