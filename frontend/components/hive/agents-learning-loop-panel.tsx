"use client";

import type { JSX } from "react";

import { RefreshCw, Sparkles } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { toast } from "sonner";

import { ApprovalCardDeck, type ApprovalDeckItem } from "@/components/hive/approval-card-deck";
import { V4Badge, V4Card, V4CardHeader, V4Stat } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { useSwrVisiblePollOptions } from "@/lib/hooks/use-swr-refresh-interval";
import type { AgentSuggestionRow, SwarmAutonomySummaryRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface MemoryEvolutionProposal {
  id: string;
  proposal_kind: string;
  title: string;
  summary: string;
  status: string;
  importance_score: number;
}

function impactBadge(score: number): string {
  return score >= 0.7 ? "high impact" : "med impact";
}

/** Memory evolution + agent initiative approvals on the Agents control plane. */
export function AgentsLearningLoopPanel(): JSX.Element {
  const pollOptions = useSwrVisiblePollOptions(COCKPIT_POLL_BOARD_MS);
  const [memoryRows, setMemoryRows] = useState<MemoryEvolutionProposal[]>([]);
  const [suggestionRows, setSuggestionRows] = useState<AgentSuggestionRow[]>([]);
  const [memoryBusy, setMemoryBusy] = useState<string | null>(null);
  const [suggestionBusy, setSuggestionBusy] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [evolutionBusy, setEvolutionBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const { data: autonomy, mutate: mutateAutonomy } = useSWR<SwarmAutonomySummaryRow>(
    "hive/swarm-autonomy-summary",
    () => hiveGet<SwarmAutonomySummaryRow>("agents/sessions/autonomy/summary"),
    pollOptions,
  );

  const reload = useCallback(async () => {
    setLoadError(null);
    try {
      const [memory, suggestions] = await Promise.all([
        hiveGet<MemoryEvolutionProposal[]>("hive-mind/memory-evolution/proposals?status_filter=pending&limit=24"),
        hiveGet<AgentSuggestionRow[]>("agents/suggestions?status_filter=pending&limit=80"),
      ]);
      setMemoryRows(Array.isArray(memory) ? memory : []);
      setSuggestionRows(Array.isArray(suggestions) ? suggestions : []);
    } catch (err) {
      const msg = err instanceof HiveApiError ? err.message : err instanceof Error ? err.message : "Load failed";
      setLoadError(msg);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function reviewMemory(id: string, action: "approve" | "reject"): Promise<void> {
    setMemoryBusy(id);
    try {
      await hivePostJson(`hive-mind/memory-evolution/proposals/${encodeURIComponent(id)}/${action}`, {});
      toast.success(action === "approve" ? "Memory proposal approved" : "Memory proposal rejected");
      await reload();
      await mutateAutonomy();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Action failed");
    } finally {
      setMemoryBusy(null);
    }
  }

  async function reviewSuggestion(id: string, decision: "approve" | "reject"): Promise<void> {
    setSuggestionBusy(id);
    try {
      await hivePostJson(`agents/suggestions/${encodeURIComponent(id)}/review`, { decision });
      toast.success(decision === "approve" ? "Suggestion approved" : "Suggestion rejected");
      await reload();
      await mutateAutonomy();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Review failed");
    } finally {
      setSuggestionBusy(null);
    }
  }

  async function approveAllSuggestions(includeHighRisk: boolean): Promise<void> {
    const pending = suggestionRows.filter((row) => row.status === "pending");
    if (!pending.length) return;

    const highCount = pending.filter((row) => row.risk_level === "high").length;
    if (highCount > 0 && !includeHighRisk) {
      const ok = window.confirm(
        `Approve ${pending.length - highCount} safe suggestion(s)? (${highCount} high-risk skipped — use "Approve all incl. high risk" if intended.)`,
      );
      if (!ok) return;
    } else {
      const ok = window.confirm(`Approve all ${pending.length} pending suggestion(s)?`);
      if (!ok) return;
    }

    setBulkBusy(true);
    try {
      const result = await hivePostJson<{ processed: number; skipped: number; errors: string[] }>(
        "agents/suggestions/bulk-review",
        {
          decision: "approve",
          include_high_risk: includeHighRisk,
          limit: 100,
        },
      );
      toast.success(`Approved ${result.processed} · skipped ${result.skipped}`);
      if (result.errors?.length) {
        toast.error(`${result.errors.length} error(s) — check logs`);
      }
      await reload();
      await mutateAutonomy();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Bulk approve failed");
    } finally {
      setBulkBusy(false);
    }
  }

  async function rejectAllSuggestions(): Promise<void> {
    const pending = suggestionRows.filter((row) => row.status === "pending");
    if (!pending.length) return;
    const ok = window.confirm(`Reject all ${pending.length} pending suggestion(s)?`);
    if (!ok) return;

    setBulkBusy(true);
    try {
      const result = await hivePostJson<{ processed: number; skipped: number }>(
        "agents/suggestions/bulk-review",
        { decision: "reject", include_high_risk: true, limit: 100 },
      );
      toast.success(`Rejected ${result.processed}`);
      await reload();
      await mutateAutonomy();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Bulk reject failed");
    } finally {
      setBulkBusy(false);
    }
  }

  async function runEvolution(): Promise<void> {
    setEvolutionBusy(true);
    try {
      const result = await hivePostJson<{ proposals_created?: number }>("hive-mind/memory-evolution/run", {});
      toast.success(`Evolution tick complete · ${result.proposals_created ?? 0} proposals`);
      await reload();
      await mutateAutonomy();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Evolution run failed");
    } finally {
      setEvolutionBusy(false);
    }
  }

  async function handleRefresh(): Promise<void> {
    setRefreshing(true);
    try {
      await reload();
      await mutateAutonomy();
    } finally {
      setRefreshing(false);
    }
  }

  const pendingMemory = memoryRows.filter((row) => row.status === "pending");
  const pendingSuggestions = suggestionRows.filter((row) => row.status === "pending");

  const memoryDeckItems: ApprovalDeckItem[] = useMemo(
    () =>
      pendingMemory.map((row) => ({
        id: row.id,
        title: row.title || row.summary,
        description: row.summary || row.title,
        meta: `${row.proposal_kind} · confidence ${row.importance_score.toFixed(2)}`,
        badge: "memory",
        badgeTone: "gold",
      })),
    [pendingMemory],
  );

  const suggestionDeckItems: ApprovalDeckItem[] = useMemo(
    () =>
      pendingSuggestions.map((row) => ({
        id: row.id,
        title: row.title,
        description: row.description,
        meta: `${row.proposed_by_role} · impact ${(row.impact_score * 100).toFixed(0)}% · ${row.proposal_type.replace(/_/g, " ")}`,
        badge: row.risk_level === "high" ? "high risk" : impactBadge(row.impact_score),
        badgeTone: row.risk_level === "high" ? "warn" : row.impact_score >= 0.7 ? "gold" : "info",
      })),
    [pendingSuggestions],
  );

  const highRiskPending = pendingSuggestions.filter((row) => row.risk_level === "high").length;

  return (
    <V4Card id="agents-learning-loop" className="relative scroll-mt-28">
      <button
        type="button"
        aria-label="Refresh learning loop"
        className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-[12px] border border-(--qs-border) text-(--qs-text-3) hover:border-(--qs-border-2) hover:text-pollen touch-manipulation md:right-6 md:top-6"
        disabled={refreshing}
        onClick={() => void handleRefresh()}
      >
        <RefreshCw className={cn("h-5 w-5", refreshing && "animate-spin")} aria-hidden />
      </button>

      <div className="pr-12">
        <V4CardHeader
          kicker="Phase 6.0"
          title="Learning loop"
          description="Memory evolution and agent initiative — approve verified deltas before they commit to the hive mind."
        />
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <V4Badge tone="purple">
          {(autonomy?.pending_memory_approvals ?? pendingMemory.length) +
            (autonomy?.pending_initiative_approvals ?? pendingSuggestions.length)}{" "}
          pending
        </V4Badge>
        <button
          type="button"
          disabled={evolutionBusy}
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
          onClick={() => void runEvolution()}
        >
          <Sparkles className="h-3.5 w-3.5" aria-hidden />
          Run evolution
        </button>
      </div>

      {autonomy ? (
        <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <V4Stat label="Autonomy mode" value={autonomy.autonomy_mode} valueVariant="text" />
          <V4Stat
            label="Strategy score"
            value={autonomy.average_strategy_score.toFixed(2)}
            valueVariant="text"
          />
          <V4Stat label="Reflection entries" value={autonomy.reflection_entries} valueVariant="text" />
          <V4Stat label="Long-horizon routines" value={autonomy.active_long_horizon_routines} valueVariant="text" />
        </div>
      ) : null}

      {loadError ? <p className="mb-3 text-sm text-(--qs-red)">{loadError}</p> : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)]">
        <section>
          <div className="mb-3 flex items-center justify-between gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">
              Memory evolution
            </h3>
            <V4Badge tone="gold">{pendingMemory.length} pending</V4Badge>
          </div>
          <ApprovalCardDeck
            items={memoryDeckItems}
            busyId={memoryBusy}
            emptyLabel="No pending memory proposals."
            onApprove={(id) => reviewMemory(id, "approve")}
            onReject={(id) => reviewMemory(id, "reject")}
          />
        </section>

        <section>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">
              Agent suggestions
            </h3>
            <div className="flex flex-wrap items-center gap-2">
              <V4Badge tone="purple">{pendingSuggestions.length} pending</V4Badge>
              {highRiskPending > 0 ? (
                <V4Badge tone="warn">{highRiskPending} high risk</V4Badge>
              ) : null}
            </div>
          </div>
          <ApprovalCardDeck
            items={suggestionDeckItems}
            busyId={suggestionBusy}
            bulkBusy={bulkBusy}
            emptyLabel="No pending initiative suggestions."
            onApprove={(id) => reviewSuggestion(id, "approve")}
            onReject={(id) => reviewSuggestion(id, "reject")}
            onApproveAll={() => approveAllSuggestions(false)}
            onRejectAll={() => rejectAllSuggestions()}
          />
          {highRiskPending > 0 ? (
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm mt-3 w-full"
              disabled={bulkBusy || suggestionBusy !== null}
              onClick={() => void approveAllSuggestions(true)}
            >
              Approve all including {highRiskPending} high-risk
            </button>
          ) : null}
        </section>
      </div>
    </V4Card>
  );
}
