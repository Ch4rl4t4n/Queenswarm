/** Sub-swarm global sync countdown helpers. */

import { formatDurationSeconds } from "@/lib/format-relative-time";

export function formatSyncDue(seconds: number): string {
  if (seconds <= 0) return "due now";
  return formatDurationSeconds(seconds, { style: "verbose" });
}

export function syncTone(needsSync: boolean): "ok" | "warn" | "info" {
  if (needsSync) return "warn";
  return "ok";
}

export function memberCapacityTone(memberCount: number, recommended: number): "ok" | "warn" | "info" {
  if (memberCount === 0) return "warn";
  if (memberCount > recommended) return "info";
  return "ok";
}
