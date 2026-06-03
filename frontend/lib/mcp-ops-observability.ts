import { formatTimeAgoMinutes } from "@/lib/format-relative-time";

export const MCP_SNAPSHOT_FRESHNESS_FRESH_MAX_MINUTES = 10;
export const MCP_SNAPSHOT_FRESHNESS_AGING_MAX_MINUTES = 60;
export const MCP_SNAPSHOT_RETRY_SPIKE_24H_THRESHOLD = 3;
export const MCP_LIFECYCLE_RECOMMENDATION_COOLDOWN_MINUTES = 5;

export type McpSnapshotFreshnessTone = "fresh" | "aging" | "stale";

export interface McpSnapshotFreshness {
  tone: McpSnapshotFreshnessTone;
  ageMinutes: number | null;
}

export function minutesSinceIso(input: string | null): number | null {
  if (!input) return null;
  const parsed = new Date(input);
  if (Number.isNaN(parsed.getTime())) return null;
  return Math.max(0, Math.round((Date.now() - parsed.getTime()) / 60_000));
}

export function resolveMcpSnapshotFreshness(input: string | null): McpSnapshotFreshness {
  const ageMinutes = minutesSinceIso(input);
  if (ageMinutes === null) {
    return { tone: "stale", ageMinutes: null };
  }
  if (ageMinutes <= MCP_SNAPSHOT_FRESHNESS_FRESH_MAX_MINUTES) {
    return { tone: "fresh", ageMinutes };
  }
  if (ageMinutes <= MCP_SNAPSHOT_FRESHNESS_AGING_MAX_MINUTES) {
    return { tone: "aging", ageMinutes };
  }
  return { tone: "stale", ageMinutes };
}

export function formatRelativeMinutes(minutes: number | null): string {
  return formatTimeAgoMinutes(minutes);
}
