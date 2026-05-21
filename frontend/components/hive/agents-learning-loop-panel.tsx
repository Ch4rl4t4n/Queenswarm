"use client";

import type { JSX } from "react";

import { Check, RefreshCw, Sparkles, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import useSWR from "swr";
import { toast } from "sonner";

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

/** Memory evolution + agent initiative approvals on the Agents control plane. */
export function AgentsLearningLoopPanel(): JSX.Element {
  const pollOptions = useSwrVisiblePollOptions(COCKPIT_POLL_BOARD_MS);
  const [memoryRows, setMemoryRows] = useState<MemoryEvolutionProposal[]>([]);
  const [suggestionRows, setSuggestionRows] = useState<AgentSuggestionRow[]>([]);
  const [memoryBusy, setMemoryBusy] = useState<string | null>(null);
  const [suggestionBusy, setSuggestionBusy] = useState<string | null>(null);
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
        hiveGet<MemoryEvolutionProposal[]>("hive-mind/memory-evolution/proposals?status_filter=pending&limit=12"),
        hiveGet<AgentSuggestionRow[]>("agents/suggestions?status_filter=pending&limit=12"),
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

      <div className="grid gap-4 lg:grid-cols-2">
        <section>
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">
              Memory evolution
            </h3>
            <V4Badge tone="gold">{pendingMemory.length} pending</V4Badge>
          </div>
          {!pendingMemory.length ? (
            <p className="text-sm text-(--qs-text-3)">No pending memory proposals.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {pendingMemory.map((row) => (
                <article key={row.id} className="v4-spawn-rule">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-(--qs-text)">{row.title || row.summary}</p>
                    <p className="mt-1 text-[11px] text-(--qs-text-3)">
                      {row.proposal_kind} · confidence {row.importance_score.toFixed(2)}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
                      disabled={memoryBusy === row.id}
                      onClick={() => void reviewMemory(row.id, "reject")}
                    >
                      <X className="h-3.5 w-3.5" aria-hidden />
                    </button>
                    <button
                      type="button"
                      className={cn("qs-btn qs-btn--primary qs-btn--sm gap-1")}
                      disabled={memoryBusy === row.id}
                      onClick={() => void reviewMemory(row.id, "approve")}
                    >
                      <Check className="h-3.5 w-3.5" aria-hidden />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">
              Agent suggestions
            </h3>
            <V4Badge tone="purple">{pendingSuggestions.length} pending</V4Badge>
          </div>
          {!pendingSuggestions.length ? (
            <p className="text-sm text-(--qs-text-3)">No pending initiative suggestions.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {pendingSuggestions.map((row) => (
                <article key={row.id} className="v4-suggestion-row">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-(--qs-text)">{row.title}</p>
                    <p className="mt-1 line-clamp-2 text-xs text-(--qs-text-2)">{row.description}</p>
                    <p className="mt-1 text-[10px] text-(--qs-text-3)">
                      {row.proposed_by_role} · impact {(row.impact_score * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm"
                      disabled={suggestionBusy === row.id}
                      onClick={() => void reviewSuggestion(row.id, "reject")}
                    >
                      Reject
                    </button>
                    <button
                      type="button"
                      className="qs-btn qs-btn--primary qs-btn--sm"
                      disabled={suggestionBusy === row.id}
                      onClick={() => void reviewSuggestion(row.id, "approve")}
                    >
                      Approve
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </V4Card>
  );
}
