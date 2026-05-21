/** Sub-swarm global sync countdown helpers. */

export function formatSyncDue(seconds: number): string {
  if (seconds <= 0) return "due now";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
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
