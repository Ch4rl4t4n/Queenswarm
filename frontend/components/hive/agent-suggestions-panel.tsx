"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ApprovalCardDeck, type ApprovalDeckItem } from "@/components/hive/approval-card-deck";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import type { AgentSuggestionRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface AgentSuggestionsPanelProps {
  className?: string;
}

function impactBadge(score: number): string {
  return score >= 0.7 ? "high impact" : "med impact";
}

export function AgentSuggestionsPanel({ className }: AgentSuggestionsPanelProps) {
  const [rows, setRows] = useState<AgentSuggestionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const body = await hiveGet<AgentSuggestionRow[]>("agents/suggestions?status_filter=pending&limit=80");
      setRows(Array.isArray(body) ? body : []);
    } catch (err) {
      setError(err instanceof HiveApiError ? err.message : "Unable to load suggestions");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, DASHBOARD_BOOT_STAGGER_MS.agentSuggestions);
    return () => window.clearTimeout(timer);
  }, [load]);

  const pending = useMemo(() => rows.filter((item) => item.status === "pending"), [rows]);

  const deckItems: ApprovalDeckItem[] = useMemo(
    () =>
      pending.map((row) => ({
        id: row.id,
        title: row.title,
        description: row.description,
        meta: `${row.proposed_by_role} · ${row.proposal_type.replace(/_/g, " ")}`,
        badge: row.risk_level === "high" ? "high risk" : impactBadge(row.impact_score),
        badgeTone: row.risk_level === "high" ? "warn" : row.impact_score >= 0.7 ? "gold" : "info",
      })),
    [pending],
  );

  async function review(id: string, decision: "approve" | "reject"): Promise<void> {
    setBusyId(id);
    setError(null);
    try {
      const updated = await hivePostJson<AgentSuggestionRow>(
        `agents/suggestions/${encodeURIComponent(id)}/review`,
        { decision },
      );
      setRows((prev) => prev.map((row) => (row.id === id ? updated : row)));
    } catch (err) {
      setError(err instanceof HiveApiError ? err.message : "Review failed");
    } finally {
      setBusyId(null);
    }
  }

  async function approveAll(includeHighRisk: boolean): Promise<void> {
    if (!pending.length) return;
    const high = pending.filter((r) => r.risk_level === "high").length;
    const ok = window.confirm(
      includeHighRisk || high === 0
        ? `Approve all ${pending.length} pending?`
        : `Approve ${pending.length - high} safe (skip ${high} high-risk)?`,
    );
    if (!ok) return;
    setBulkBusy(true);
    try {
      await hivePostJson("agents/suggestions/bulk-review", {
        decision: "approve",
        include_high_risk: includeHighRisk,
        limit: 100,
      });
      await load();
    } catch (err) {
      setError(err instanceof HiveApiError ? err.message : "Bulk approve failed");
    } finally {
      setBulkBusy(false);
    }
  }

  return (
    <V4Card id="agent-suggestions" className={cn("v4-card-interactive scroll-mt-28", className)}>
      <V4CardHeader
        title="Agent suggestions"
        description="Self-proposed improvements — one card at a time, approve to advance."
        actions={
          <>
            <V4Badge tone="purple">{pending.length} pending</V4Badge>
            <button type="button" onClick={() => void load()} className="qs-btn qs-btn--ghost qs-btn--sm">
              Refresh
            </button>
          </>
        }
      />

      {loading ? <p className="text-sm text-(--qs-text-3)">Loading initiative suggestions…</p> : null}

      {!loading ? (
        <ApprovalCardDeck
          items={deckItems}
          busyId={busyId}
          bulkBusy={bulkBusy}
          emptyLabel="No pending suggestions. Agents propose after reflection cycles complete."
          onApprove={(id) => review(id, "approve")}
          onReject={(id) => review(id, "reject")}
          onApproveAll={() => approveAll(false)}
        />
      ) : null}

      {error ? <p className="mt-3 text-sm text-(--qs-red)">{error}</p> : null}
    </V4Card>
  );
}
