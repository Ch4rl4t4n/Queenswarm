"use client";

import { AgentSuggestionsConfigurationsPanel } from "@/components/hive/agent-suggestions-configurations-panel";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { MemoryEvolutionProposalsPanel } from "@/components/hive/memory-evolution-proposals-panel";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { V4Badge, V4Card, V4CardHeader, V4Stat } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { useSwrVisiblePollOptions } from "@/lib/hooks/use-swr-refresh-interval";
import type {
  AgentInitiativePolicy,
  AgentSuggestionRow,
  MemoryEvolutionPolicy,
  MemoryEvolutionProposalRow,
  SwarmAutonomySummaryRow,
} from "@/lib/hive-types";
import { Sparkles } from "lucide-react";
import type { JSX } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { toast } from "sonner";

/** Memory evolution + agent initiative approvals on the Agents control plane. */
export function AgentsLearningLoopPanel(): JSX.Element {
  const pollOptions = useSwrVisiblePollOptions(COCKPIT_POLL_BOARD_MS);
  const [memoryRows, setMemoryRows] = useState<MemoryEvolutionProposalRow[]>([]);
  const [memoryPolicy, setMemoryPolicy] = useState<MemoryEvolutionPolicy>({
    auto_approve_enabled: false,
    include_high_importance: false,
  });
  const [suggestionRows, setSuggestionRows] = useState<AgentSuggestionRow[]>([]);
  const [memoryBusy, setMemoryBusy] = useState<string | null>(null);
  const [memoryBulkBusy, setMemoryBulkBusy] = useState(false);
  const [suggestionBusy, setSuggestionBusy] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [evolutionBusy, setEvolutionBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [initiativePolicy, setInitiativePolicy] = useState<AgentInitiativePolicy>({
    auto_approve_enabled: false,
    include_high_risk: false,
  });
  const autoApproveLock = useRef(false);

  const { data: autonomy, mutate: mutateAutonomy } = useSWR<SwarmAutonomySummaryRow>(
    "hive/swarm-autonomy-summary",
    () => hiveGet<SwarmAutonomySummaryRow>("agents/sessions/autonomy/summary"),
    pollOptions,
  );

  const reload = useCallback(async () => {
    setLoadError(null);
    try {
      const [memory, suggestions, policy, memoryPolicyRow] = await Promise.all([
        hiveGet<MemoryEvolutionProposalRow[]>("hive-mind/memory-evolution/proposals?status_filter=pending&limit=80"),
        hiveGet<AgentSuggestionRow[]>("agents/suggestions?status_filter=pending&limit=80"),
        hiveGet<AgentInitiativePolicy>("agents/suggestions/policy"),
        hiveGet<MemoryEvolutionPolicy>("hive-mind/memory-evolution/policy"),
      ]);
      setMemoryRows(Array.isArray(memory) ? memory : []);
      setSuggestionRows(Array.isArray(suggestions) ? suggestions : []);
      setInitiativePolicy(policy);
      setMemoryPolicy(memoryPolicyRow);
    } catch (err) {
      const msg = err instanceof HiveApiError ? err.message : err instanceof Error ? err.message : "Load failed";
      setLoadError(msg);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const drainAutoApprove = useCallback(async (): Promise<void> => {
    if (autoApproveLock.current || !initiativePolicy.auto_approve_enabled) {
      return;
    }
    autoApproveLock.current = true;
    try {
      for (let round = 0; round < 8; round += 1) {
        const result = await hivePostJson<{ processed: number }>("agents/suggestions/bulk-review", {
          decision: "approve",
          include_high_risk: initiativePolicy.include_high_risk,
          limit: 50,
        });
        if ((result.processed ?? 0) === 0) {
          break;
        }
        await reload();
        await mutateAutonomy();
      }
    } catch {
      /* server drain on GET also applies */
    } finally {
      autoApproveLock.current = false;
    }
  }, [initiativePolicy.auto_approve_enabled, initiativePolicy.include_high_risk, mutateAutonomy, reload]);

  useEffect(() => {
    if (!initiativePolicy.auto_approve_enabled) {
      return;
    }
    void drainAutoApprove();
    const interval = window.setInterval(() => {
      void reload();
    }, 90_000);
    return () => window.clearInterval(interval);
  }, [drainAutoApprove, initiativePolicy.auto_approve_enabled, reload]);

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
        `Approve ${pending.length - highCount} safe suggestion(s)? (${highCount} high-risk skipped.)`,
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
        { decision: "approve", include_high_risk: includeHighRisk, limit: 100 },
      );
      toast.success(`Approved ${result.processed} · skipped ${result.skipped}`);
      await reload();
      await mutateAutonomy();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Bulk approve failed");
    } finally {
      setBulkBusy(false);
    }
  }

  async function approveAllMemory(includeHighImportance: boolean): Promise<void> {
    const pending = memoryRows.filter((row) => row.status === "pending");
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
    setMemoryBulkBusy(true);
    try {
      const result = await hivePostJson<{ processed: number; skipped: number }>(
        "hive-mind/memory-evolution/proposals/bulk-review",
        { decision: "approve", include_high_importance: includeHighImportance, limit: 100 },
      );
      toast.success(`Approved ${result.processed} · skipped ${result.skipped}`);
      await reload();
      await mutateAutonomy();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Bulk approve failed");
    } finally {
      setMemoryBulkBusy(false);
    }
  }

  async function clearAllMemory(): Promise<void> {
    setMemoryBulkBusy(true);
    try {
      const result = await hivePostJson<{ processed: number }>(
        "hive-mind/memory-evolution/proposals/bulk-review",
        { decision: "reject", include_high_importance: true, limit: 100 },
      );
      toast.success(`Cleared ${result.processed} proposal${result.processed === 1 ? "" : "s"}`);
      await reload();
      await mutateAutonomy();
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Clear all failed");
    } finally {
      setMemoryBulkBusy(false);
    }
  }

  async function rejectAllSuggestions(): Promise<void> {
    setBulkBusy(true);
    try {
      const result = await hivePostJson<{ processed: number }>("agents/suggestions/bulk-review", {
        decision: "reject",
        include_high_risk: true,
        limit: 100,
      });
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

  return (
    <div className="space-y-6">
      <V4Card id="agents-learning-loop" className="scroll-mt-28">
        <V4CardHeader
          kicker="Phase 6.0"
          title="Learning loop"
          description="Memory evolution and swarm autonomy — approve verified deltas before they commit to the hive mind."
          hint={sectionHintNode("agentsLearning")}
          actions={<HiveRefreshButton busy={refreshing} onClick={() => void handleRefresh()} />}
        />

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
            <V4Stat label="Strategy score" value={autonomy.average_strategy_score.toFixed(2)} valueVariant="text" />
            <V4Stat label="Reflection entries" value={autonomy.reflection_entries} valueVariant="text" />
            <V4Stat label="Long-horizon routines" value={autonomy.active_long_horizon_routines} valueVariant="text" />
          </div>
        ) : null}

        {loadError ? <p className="mb-3 text-sm text-(--qs-red)">{loadError}</p> : null}

        <section>
          <div className="mb-3 flex items-center justify-between gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">Memory evolution</h3>
            <V4Badge tone="gold">{pendingMemory.length} pending</V4Badge>
          </div>
          <MemoryEvolutionProposalsPanel
            rows={memoryRows}
            policy={memoryPolicy}
            busyId={memoryBusy}
            bulkBusy={memoryBulkBusy}
            policyBusy={false}
            onPolicyChange={setMemoryPolicy}
            onReload={reload}
            onReview={reviewMemory}
            onApproveAll={approveAllMemory}
            onClearAll={clearAllMemory}
          />
        </section>
      </V4Card>

      <V4Card id="agent-suggestions">
        <V4CardHeader
          title="Agent suggestions"
          description="Reflection · initiative · workflow deltas · auto-approve rules."
        />
        <AgentSuggestionsConfigurationsPanel
          rows={suggestionRows}
          policy={initiativePolicy}
          busyId={suggestionBusy}
          bulkBusy={bulkBusy}
          policyBusy={false}
          onPolicyChange={setInitiativePolicy}
          onReload={reload}
          onReview={reviewSuggestion}
          onApproveAll={approveAllSuggestions}
          onRejectAll={rejectAllSuggestions}
        />
      </V4Card>
    </div>
  );
}
