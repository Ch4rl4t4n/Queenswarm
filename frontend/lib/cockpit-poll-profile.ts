/**
 * Cockpit polling cadence — tune for ~16 GB operator hosts by stretching intervals (less churn, fewer wakeups).
 *
 * Set in `.env` for the **frontend build**:
 * `NEXT_PUBLIC_QS_POLL_PROFILE=low_ram`
 */

export type CockpitPollProfileName = "default" | "low_ram" | "vps_32gb";

export function readCockpitPollProfile(): CockpitPollProfileName {
  const raw = process.env.NEXT_PUBLIC_QS_POLL_PROFILE?.trim().toLowerCase();
  if (raw === "vps_32gb") {
    return "vps_32gb";
  }
  return raw === "low_ram" ? "low_ram" : "default";
}

const profile = readCockpitPollProfile();
const low = profile === "low_ram";
const vps = profile === "vps_32gb";

/** Default SWR refresh for agents / tasks hooks and dashboard lattice */
export const COCKPIT_POLL_AGENTS_TASKS_MS = low ? 10_000 : vps ? 7000 : 5000;

/** Hive roster boards (agents page, tasks page clients) */
export const COCKPIT_POLL_BOARD_MS = low ? 12_000 : vps ? 9000 : 8000;

/** System status panel */
export const COCKPIT_POLL_SYSTEM_STATUS_MS = low ? 20_000 : vps ? 15_000 : 12_000;

/** External projects metrics auto-refresh while a project is selected */
export const COCKPIT_POLL_EXTERNAL_METRICS_MS = low ? 45_000 : vps ? 35_000 : 25_000;

/** Main colony dashboard telemetry sweep (agents/tasks/system pulse). */
export const COCKPIT_POLL_COLONY_TELEMETRY_MS = low ? 14_000 : vps ? 12_000 : 10_000;

/** Workflows DAG list refresh */
export const COCKPIT_POLL_WORKFLOWS_MS = low ? 15_000 : vps ? 12_000 : 8000;

/** Swarm manager console roster */
export const COCKPIT_POLL_SWARM_MANAGER_MS = low ? 14_000 : vps ? 12_000 : 10_000;

/** Jobs poll console when auto-refresh is enabled */
export const COCKPIT_POLL_JOBS_MS = low ? 8000 : vps ? 6000 : 4000;

/** Dashboard workflow board widget */
export const COCKPIT_POLL_WORKFLOW_BOARD_MS = low ? 60_000 : vps ? 50_000 : 50_000;

/** Embedded task queue section */
export const COCKPIT_POLL_TASK_QUEUE_MS = low ? 55_000 : vps ? 45_000 : 45_000;

/** Swarm board section on dashboard */
export const COCKPIT_POLL_SWARM_BOARD_MS = low ? 75_000 : vps ? 60_000 : 60_000;

/** Live task drawer status poll while bee is working */
export const COCKPIT_POLL_TASK_DRAWER_MS = low ? 5000 : vps ? 4000 : 3000;

/** Browser harness session list */
export const COCKPIT_POLL_BROWSER_SESSIONS_MS = low ? 8000 : vps ? 6000 : 5000;

/** Browser harness action log for selected session */
export const COCKPIT_POLL_BROWSER_ACTIONS_MS = low ? 6000 : vps ? 4500 : 3500;

/** Agents page mini hive-mind graph strip */
export const COCKPIT_POLL_HIVE_MIND_GRAPH_MS = low ? 90_000 : vps ? 75_000 : 60_000;
