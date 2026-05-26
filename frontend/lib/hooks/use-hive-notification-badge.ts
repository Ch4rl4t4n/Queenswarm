"use client";

import { useOperatorPendingSnapshot } from "@/lib/hooks/use-operator-pending-snapshot";
import type { DashboardSummary } from "@/lib/hive-types";

/** Format badge count for header/sidebar (cap at 9+). */
export function formatHiveNotificationBadge(total: number): string | null {
  if (total <= 0) return null;
  return total > 9 ? "9+" : String(total);
}

/**
 * Actionable operator alerts for the mobile header bell (tasks + pending review + Execution Studio).
 */
export function useHiveNotificationBadge(summary: DashboardSummary | null): string | null {
  const snapshot = useOperatorPendingSnapshot(summary?.tasks.pending ?? 0);
  return formatHiveNotificationBadge(snapshot.total);
}
