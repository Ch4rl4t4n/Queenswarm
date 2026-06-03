"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { MemoryEvolutionProposalsPanel } from "@/components/hive/memory-evolution-proposals-panel";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { MemoryEvolutionPolicy, MemoryEvolutionProposalRow } from "@/lib/hive-types";

/** Pending memory evolution proposals — approve / reject via hive-mind API. */
export function MemoryEvolutionPanel() {
  const [rows, setRows] = useState<MemoryEvolutionProposalRow[]>([]);
  const [policy, setPolicy] = useState<MemoryEvolutionPolicy>({
    auto_approve_enabled: false,
    include_high_importance: false,
  });
  const [busyId, setBusyId] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const [proposals, nextPolicy] = await Promise.all([
        hiveGet<MemoryEvolutionProposalRow[]>(
          "hive-mind/memory-evolution/proposals?status_filter=pending&limit=80",
        ),
        hiveGet<MemoryEvolutionPolicy>("hive-mind/memory-evolution/policy"),
      ]);
      setRows(Array.isArray(proposals) ? proposals : []);
      setPolicy(nextPolicy);
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Proposals unavailable";
      setErr(msg);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function review(id: string, action: "approve" | "reject") {
    setBusyId(id);
    try {
      await hivePostJson(`hive-mind/memory-evolution/proposals/${encodeURIComponent(id)}/${action}`, {});
      toast.success(action === "approve" ? "Proposal approved" : "Proposal rejected");
      await reload();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  }

  async function approveAll(includeHighImportance: boolean) {
    const pending = rows.filter((row) => row.status === "pending");
    if (!pending.length) return;
    const highCount = pending.filter((row) => row.importance_score >= 0.82).length;
    if (highCount > 0 && !includeHighImportance) {
      const ok = window.confirm(
        `Approve ${pending.length - highCount} routine proposal(s)? (${highCount} high-importance skipped.)`,
      );
      if (!ok) return;
    } else {
      const ok = window.confirm(`Approve all ${pending.length} pending proposal(s)?`);
      if (!ok) return;
    }
    setBulkBusy(true);
    try {
      const result = await hivePostJson<{ processed: number; skipped: number }>(
        "hive-mind/memory-evolution/proposals/bulk-review",
        { decision: "approve", include_high_importance: includeHighImportance, limit: 100 },
      );
      toast.success(`Approved ${result.processed} · skipped ${result.skipped}`);
      await reload();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Bulk approve failed");
    } finally {
      setBulkBusy(false);
    }
  }

  async function clearAll() {
    setBulkBusy(true);
    try {
      const result = await hivePostJson<{ processed: number }>(
        "hive-mind/memory-evolution/proposals/bulk-review",
        { decision: "reject", include_high_importance: true, limit: 100 },
      );
      toast.success(`Cleared ${result.processed} proposal${result.processed === 1 ? "" : "s"}`);
      await reload();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Clear all failed");
    } finally {
      setBulkBusy(false);
    }
  }

  const pendingCount = rows.filter((row) => row.status === "pending").length;

  return (
    <V4Card>
      <V4CardHeader
        title="Memory evolution proposals"
        description="Suggested graph edits from reflection cycles — approve to commit, reject to discard."
        actions={<V4Badge tone="purple">{pendingCount} pending</V4Badge>}
      />
      {err ? <p className="mb-3 text-sm text-(--qs-red)">{err}</p> : null}
      <MemoryEvolutionProposalsPanel
        rows={rows}
        policy={policy}
        busyId={busyId}
        bulkBusy={bulkBusy}
        policyBusy={false}
        onPolicyChange={setPolicy}
        onReload={reload}
        onReview={review}
        onApproveAll={approveAll}
        onClearAll={clearAll}
      />
    </V4Card>
  );
}
