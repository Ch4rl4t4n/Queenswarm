"use client";

import { useEffect, useState } from "react";

import { hiveGet } from "@/lib/api";
import type { DashboardSummary, PendingReviewStats } from "@/lib/hive-types";

/** Caps mobile bell badge at 9; returns 0 when nothing actionable. */
export function formatHiveNotificationBadge(count: number): string | null {
  if (count <= 0) {
    return null;
  }
  return count > 9 ? "9+" : String(count);
}

/**
 * Actionable operator alerts for the mobile header bell (tasks + pending review).
 */
export function useHiveNotificationBadge(summary: DashboardSummary | null): string | null {
  const [pendingReview, setPendingReview] = useState(0);

  useEffect(() => {
    let alive = true;
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const stats = await hiveGet<PendingReviewStats>("learning/pending-review/stats");
          if (alive) {
            setPendingReview(Math.max(0, stats.pending_count ?? 0));
          }
        } catch {
          /* keep last count */
        }
      })();
    }, 600);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, []);

  const total = (summary?.tasks.pending ?? 0) + pendingReview;
  return formatHiveNotificationBadge(total);
}
