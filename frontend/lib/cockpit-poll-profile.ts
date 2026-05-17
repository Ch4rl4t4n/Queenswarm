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
export const COCKPIT_POLL_COLONY_TELEMETRY_MS = low ? 14_000 : vps ? 10_000 : 8000;
