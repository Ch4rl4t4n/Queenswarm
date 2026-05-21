"use client";

import { CheckIcon, Loader2Icon, ShieldAlertIcon, XIcon } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import type { PendingReviewItemRow, PendingReviewStats } from "@/lib/hive-types";

function fmtConfidence(fraction: number | null): string {
  if (fraction === null || Number.isNaN(fraction)) return "—";
  return `${(fraction * 100).toFixed(1)}%`;
}

function reasonLabel(reason: string): string {
  return reason.replaceAll("_", " ");
}

/** Operator queue for sub-threshold confidence outcomes (< 75% default). */
export function PendingReviewPanel(): JSX.Element {
  const [items, setItems] = useState<PendingReviewItemRow[]>([]);
  const [stats, setStats] = useState<PendingReviewStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [queue, counts] = await Promise.all([
        hiveGet<PendingReviewItemRow[]>("learning/pending-review?limit=20"),
        hiveGet<PendingReviewStats>("learning/pending-review/stats"),
      ]);
      setItems(queue);
      setStats(counts);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Pending review unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useIntervalWhenVisible(() => void load(), COCKPIT_POLL_COLONY_TELEMETRY_MS);

  const resolve = async (itemId: string, action: "approve" | "reject") => {
    setBusyId(itemId);
    try {
      await hivePostJson(`learning/pending-review/${itemId}/resolve`, { action });
      toast.success(action === "approve" ? "Outcome approved" : "Outcome rejected");
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Resolution failed.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <V4Card>
      <V4CardHeader
        title="Pending review queue"
        description="Outcomes below confidence gate · human approval before release"
        actions={
          <V4Badge tone={stats?.pending_count ? "warn" : "info"}>
            <ShieldAlertIcon className="mr-1 inline h-3 w-3" aria-hidden />
            {stats?.pending_count ?? 0} waiting
          </V4Badge>
        }
      />
      {loading ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden />
          Loading review queue…
        </p>
      ) : null}
      {err ? <p className="text-sm text-danger">{err}</p> : null}
      {!loading && !err && items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No items awaiting review — hive gate is clear.</p>
      ) : null}
      <ul className="mt-3 space-y-3">
        {items.map((item) => (
          <li
            key={item.id}
            className="rounded-xl border border-alert/30 bg-black/25 p-3 text-sm"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase text-pollen">
                {reasonLabel(item.reason)}
              </span>
              <span className="text-xs text-cyan">confidence {fmtConfidence(item.confidence_fraction)}</span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              swarm {item.swarm_id.slice(0, 8)}… · task {item.task_id?.slice(0, 8) ?? "n/a"}
            </p>
            <div className="v4-pending-review-actions mt-3 flex gap-2">
              <button
                type="button"
                disabled={busyId === item.id}
                onClick={() => void resolve(item.id, "approve")}
                className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1 text-success"
              >
                {busyId === item.id ? <Loader2Icon className="h-3 w-3 animate-spin" /> : <CheckIcon className="h-3 w-3" />}
                Approve
              </button>
              <button
                type="button"
                disabled={busyId === item.id}
                onClick={() => void resolve(item.id, "reject")}
                className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1 text-danger"
              >
                <XIcon className="h-3 w-3" />
                Reject
              </button>
            </div>
          </li>
        ))}
      </ul>
    </V4Card>
  );
}
