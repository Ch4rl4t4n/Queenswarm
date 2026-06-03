"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { HiveSwitch } from "@/components/ui/hive-switch";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, type V4BadgeTone } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { CodebaseLane, HandledProposal, PendingProposal, StudioPolicy } from "@/lib/execution-studio-shared-types";
import { dispatchOperatorPendingRefresh } from "@/lib/operator-pending-events";
import { formatTimeAgoIso } from "@/lib/format-relative-time";
import { cn } from "@/lib/utils";

type RiskFilter = "all" | "low" | "medium" | "high";

const SCV_PENDING_PREVIEW_LIMIT = 3;
const SCV_HANDLED_PREVIEW_LIMIT = 5;

export interface ScvPendingProposalsPanelProps {
  pendingProposals: PendingProposal[];
  pendingProposalsTotal?: number;
  policy: StudioPolicy;
  codebase: CodebaseLane;
  policyBusy: boolean;
  proposalBusyId: string | null;
  onPatchPolicy: (
    patch: Partial<StudioPolicy>,
  ) => Promise<{ policy: StudioPolicy; codebase_auto_approve?: CodebaseAutoApproveResult } | void>;
  onReview: (proposalId: string, decision: "approve" | "reject") => Promise<void>;
  onReloadOverview: (opts?: { silent?: boolean }) => Promise<void>;
}

interface CodebaseAutoApproveResult {
  processed: number;
  skipped: number;
  errors?: string[];
}

interface CodebaseProposalApiItem {
  id: string;
  title: string;
  description: string;
  proposed_by_role: string;
  risk_level: string;
  status?: string;
  reviewed_at?: string | null;
  reviewed_by_subject?: string | null;
  created_at: string | null;
  proposal_payload?: {
    goal_excerpt?: string;
    handoff_session_id?: string;
  };
}

function mapCodebaseProposalItem(item: CodebaseProposalApiItem): PendingProposal {
  return {
    id: item.id,
    title: item.title,
    description: item.description,
    proposed_by_role: item.proposed_by_role,
    risk_level: item.risk_level,
    created_at: item.created_at,
    goal_excerpt: item.proposal_payload?.goal_excerpt ?? "",
  };
}

function mapHandledProposalItem(item: CodebaseProposalApiItem): HandledProposal {
  return {
    ...mapCodebaseProposalItem(item),
    status: (item.status === "rejected" ? "rejected" : "approved") as "approved" | "rejected",
    reviewed_at: item.reviewed_at ?? null,
    reviewed_by_subject: item.reviewed_by_subject ?? null,
    handoff_session_id: item.proposal_payload?.handoff_session_id ?? null,
  };
}

function isAutoApproved(reviewer: string | null | undefined): boolean {
  const subject = (reviewer ?? "").trim().toLowerCase();
  return subject.startsWith("execution_studio:auto") || subject === "supervisor:auto";
}

function shortProposalId(id: string): string {
  const compact = id.replace(/-/g, "").slice(0, 4).toUpperCase();
  return `P-${compact}`;
}

function riskBadgeTone(risk: string): V4BadgeTone {
  const normalized = risk.trim().toLowerCase();
  if (normalized === "low") return "ok";
  if (normalized === "high") return "err";
  return "warn";
}


function ScvSkillBadge({ slug }: { slug: string }): JSX.Element {
  return (
    <span className="inline-flex max-w-full items-center rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-(family-name:--font-jetbrains-mono) text-[10px] text-emerald-200">
      {slug}
    </span>
  );
}

function ScvPendingProposalsPanelInner({
  pendingProposals,
  pendingProposalsTotal,
  policy,
  codebase,
  policyBusy,
  proposalBusyId,
  onPatchPolicy,
  onReview,
  onReloadOverview,
}: ScvPendingProposalsPanelProps): JSX.Element {
  const [query, setQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("all");
  const [showAllProposals, setShowAllProposals] = useState(false);
  const [autoApproveBusy, setAutoApproveBusy] = useState(false);
  const [loadedProposals, setLoadedProposals] = useState<PendingProposal[]>(pendingProposals);
  const [fetchAllBusy, setFetchAllBusy] = useState(false);
  const [recentHandled, setRecentHandled] = useState<HandledProposal[]>([]);
  const [recentBusy, setRecentBusy] = useState(false);
  const [showAllHandled, setShowAllHandled] = useState(false);
  const autoApproveLock = useRef(false);

  useEffect(() => {
    setLoadedProposals(pendingProposals);
    setShowAllProposals(false);
  }, [pendingProposals]);

  const loadRecentHandled = useCallback(async (limit = SCV_HANDLED_PREVIEW_LIMIT): Promise<void> => {
    setRecentBusy(true);
    try {
      const out = await hiveGet<{ items: CodebaseProposalApiItem[] }>(
        `execution-studio/proposals?status=approved&limit=${limit}`,
      );
      setRecentHandled(out.items.map(mapHandledProposalItem));
    } catch {
      /* keep last list */
    } finally {
      setRecentBusy(false);
    }
  }, []);

  useEffect(() => {
    void loadRecentHandled();
  }, [loadRecentHandled, pendingProposals]);

  const pendingTotal = pendingProposalsTotal ?? loadedProposals.length;
  const hasActiveFilter = query.trim().length > 0 || riskFilter !== "all";

  const resolverSkills = useMemo(
    () => [...codebase.agent_skills, ...codebase.agent_roles].filter(Boolean).slice(0, 8),
    [codebase.agent_roles, codebase.agent_skills],
  );

  const filteredProposals = useMemo(() => {
    const q = query.trim().toLowerCase();
    return loadedProposals.filter((proposal) => {
      if (riskFilter !== "all" && proposal.risk_level.trim().toLowerCase() !== riskFilter) {
        return false;
      }
      if (!q) return true;
      const haystack = [
        proposal.title,
        proposal.description,
        proposal.goal_excerpt ?? "",
        proposal.proposed_by_role,
        proposal.risk_level,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [loadedProposals, query, riskFilter]);

  const queuePendingCount = hasActiveFilter ? filteredProposals.length : pendingTotal;

  const visibleProposals = useMemo(() => {
    if (showAllProposals) {
      return filteredProposals;
    }
    return filteredProposals.slice(0, SCV_PENDING_PREVIEW_LIMIT);
  }, [filteredProposals, showAllProposals]);

  const hiddenProposalCount = hasActiveFilter
    ? Math.max(0, filteredProposals.length - SCV_PENDING_PREVIEW_LIMIT)
    : Math.max(0, queuePendingCount - SCV_PENDING_PREVIEW_LIMIT);

  const loadAllProposals = useCallback(async (): Promise<void> => {
    if (fetchAllBusy || loadedProposals.length >= pendingTotal) {
      setShowAllProposals(true);
      return;
    }
    setFetchAllBusy(true);
    try {
      const out = await hiveGet<{ total: number; items: CodebaseProposalApiItem[] }>(
        `execution-studio/proposals?limit=${Math.min(100, Math.max(pendingTotal, 12))}`,
      );
      setLoadedProposals(out.items.map(mapCodebaseProposalItem));
      setShowAllProposals(true);
    } catch (exc) {
      const msg = exc instanceof HiveApiError ? exc.message : "Could not load all SCV proposals.";
      toast.error(msg);
    } finally {
      setFetchAllBusy(false);
    }
  }, [fetchAllBusy, loadedProposals.length, pendingTotal]);

  useEffect(() => {
    setShowAllProposals(false);
  }, [query, riskFilter]);

  const autoApprovePending = useCallback(async (): Promise<number> => {
    if (autoApproveLock.current || pendingTotal === 0) {
      return 0;
    }
    autoApproveLock.current = true;
    setAutoApproveBusy(true);
    let totalProcessed = 0;
    let totalSkipped = 0;
    const errorMessages: string[] = [];
    try {
      for (let round = 0; round < 10; round += 1) {
        const out = await hivePostJson<CodebaseAutoApproveResult>(
          "execution-studio/proposals/bulk-review",
          { decision: "approve", limit: 50 },
        );
        totalProcessed += out.processed;
        totalSkipped += out.skipped;
        if (out.errors?.length) {
          errorMessages.push(...out.errors.slice(0, 5));
        }
        if (out.processed === 0) {
          break;
        }
        await onReloadOverview({ silent: true });
      }

      if (totalProcessed > 0) {
        await onReloadOverview({ silent: true });
        dispatchOperatorPendingRefresh();
        await loadRecentHandled(20);
        toast.success(`Auto-approved ${totalProcessed} SCV proposal(s).`);
      } else if (pendingTotal > 0) {
        const detail =
          errorMessages[0] ??
          (totalSkipped > 0
            ? `${totalSkipped} proposal(s) could not be auto-approved.`
            : "No pending proposals were approved. Try manual approve or refresh.");
        toast.error("Auto approve did not clear the queue.", { description: detail });
      }

      if (totalSkipped > 0 && totalProcessed > 0) {
        toast.message(`${totalSkipped} proposal(s) skipped during auto-approve.`);
      }
      return totalProcessed;
    } catch (exc) {
      const msg = exc instanceof HiveApiError ? exc.message : "Auto-approve failed.";
      toast.error(msg);
      return 0;
    } finally {
      autoApproveLock.current = false;
      setAutoApproveBusy(false);
    }
  }, [loadRecentHandled, onReloadOverview, pendingTotal]);

  useEffect(() => {
    if (!policy.codebase_auto_approve_enabled) {
      return;
    }
    const tick = async () => {
      await onReloadOverview({ silent: true });
      await autoApprovePending();
    };
    void tick();
    const interval = window.setInterval(() => {
      void tick();
    }, 90_000);
    return () => window.clearInterval(interval);
  }, [autoApprovePending, onReloadOverview, policy.codebase_auto_approve_enabled]);

  const visibleHandled = showAllHandled
    ? recentHandled
    : recentHandled.slice(0, SCV_HANDLED_PREVIEW_LIMIT);

  const patchAutoApprove = useCallback(
    async (enabled: boolean) => {
      try {
        const resp = await onPatchPolicy({ codebase_auto_approve_enabled: enabled });
        if (enabled) {
          const serverProcessed = resp?.codebase_auto_approve?.processed ?? 0;
          if (serverProcessed > 0) {
            await onReloadOverview({ silent: true });
            toast.success(
              `Auto approve enabled — ${serverProcessed} pending proposal(s) approved and removed from queue.`,
            );
            return;
          }
          await autoApprovePending();
          toast.success(
            "Auto approve enabled — pending proposals approve automatically and leave this queue.",
          );
          return;
        }
        toast.success("Manual mode — approve or reject each proposal in the queue.");
      } catch {
        toast.error("Could not update auto approve policy.");
      }
    },
    [autoApprovePending, onPatchPolicy, onReloadOverview],
  );

  return (
    <div id="codebase-pending" className="qs-bubble shrink-0 space-y-4 p-4">
      <div>
        <p className="text-sm font-semibold text-(--qs-text)">SCV proposals</p>
        <p className="mt-1 text-xs text-(--qs-text-3)">
          Research → approval → Queen Maintainer handoff. Review queue shows up to{" "}
          {SCV_PENDING_PREVIEW_LIMIT} at a time ·{" "}
          <span className="font-medium text-(--qs-text-2)">{queuePendingCount} pending</span>
          {hasActiveFilter && queuePendingCount !== pendingTotal ? ` (${pendingTotal} total)` : ""}.
          {policy.codebase_auto_approve_enabled ? (
            <span className="mt-1 block text-pollen">
              Auto approve is ON — new proposals approve automatically and hand off to Queen Maintainer.
            </span>
          ) : null}
        </p>
      </div>

      <div className="flex flex-col gap-3 md:flex-row md:items-stretch">
        <input
          className="qs-input min-w-0 flex-1"
          placeholder="Filter proposals by title / role / risk…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <label
          className="flex shrink-0 items-center justify-between gap-2 rounded-lg border border-(--qs-border) bg-black/25 px-3 py-2 text-xs text-(--qs-text-2) md:min-w-[11.5rem]"
          title="Auto approve approves pending SCV proposals and removes them from this queue."
        >
          <span className="whitespace-nowrap font-medium">
            {policy.codebase_auto_approve_enabled ? "Auto approve" : "Manual"}
          </span>
          <HiveSwitch
            checked={Boolean(policy.codebase_auto_approve_enabled)}
            disabled={policyBusy || autoApproveBusy}
            aria-label="Toggle auto approve for SCV proposals"
            onCheckedChange={(checked) => void patchAutoApprove(checked)}
          />
        </label>
        <QsSelect
          className="w-full min-w-0 md:w-40 md:shrink-0"
          value={riskFilter}
          onValueChange={(next) => setRiskFilter(next as RiskFilter)}
          options={[
            { value: "all", label: "all risks" },
            { value: "low", label: "low" },
            { value: "medium", label: "medium" },
            { value: "high", label: "high" },
          ]}
        />
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--qs-text-3)">
            Proposals
            {queuePendingCount > 0 ? (
              <span className="ml-2 font-normal normal-case tracking-normal text-(--qs-text-4)">
                ({queuePendingCount})
              </span>
            ) : null}
          </p>
          {autoApproveBusy || fetchAllBusy ? (
            <span className="inline-flex items-center gap-1 text-[10px] text-(--qs-text-4)">
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
              {fetchAllBusy ? "Loading proposals…" : "Auto-approving…"}
            </span>
          ) : null}
        </div>

        <div className="v4-sessions-list-scroll hive-scrollbar">
          {filteredProposals.length === 0 ? (
            <div className="rounded-xl border border-dashed border-(--qs-border) bg-black/20 px-4 py-6 text-center">
              {pendingTotal === 0 && !hasActiveFilter ? (
                <>
                  <p className="text-sm text-(--qs-text-2)">No pending SCV proposals.</p>
                  <p className="mt-2 text-xs text-(--qs-text-3)">
                    Approved items move to Queen Maintainer sessions — see{" "}
                    <Link href="/agents" className="text-cyan underline-offset-2 hover:underline">
                      Agents → Sessions
                    </Link>{" "}
                    or the recently approved list below.
                  </p>
                </>
              ) : (
                <>
                  <p className="text-sm text-(--qs-text-2)">No proposals match this filter.</p>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm mt-3"
                    onClick={() => {
                      setQuery("");
                      setRiskFilter("all");
                    }}
                  >
                    Reset filters
                  </button>
                </>
              )}
            </div>
          ) : (
            visibleProposals.map((proposal) => (
              <div key={proposal.id} className="v4-session-row">
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex flex-wrap items-center gap-2">
                    <span className="font-(family-name:--font-jetbrains-mono) text-[11px] text-(--qs-text-3)">
                      {shortProposalId(proposal.id)}
                    </span>
                    <V4Badge tone="warn">pending</V4Badge>
                    <V4Badge tone={riskBadgeTone(proposal.risk_level)}>{proposal.risk_level}</V4Badge>
                    <V4Badge tone="gold">SCV handoff</V4Badge>
                  </div>
                  <p className="v4-session-goal text-sm font-medium text-(--qs-text)" title={proposal.title}>
                    {proposal.title}
                  </p>
                  {proposal.goal_excerpt || proposal.description ? (
                    <p className="mt-1 line-clamp-2 text-xs text-(--qs-text-3)">
                      {proposal.goal_excerpt || proposal.description}
                    </p>
                  ) : null}

                  <div className="mt-2 space-y-1.5" data-testid="scv-proposal-pattern-skills">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-3)">
                        Pattern Router
                      </p>
                      <V4Badge tone="info">heuristic-v1</V4Badge>
                      <V4Badge tone="info">{proposal.proposed_by_role}</V4Badge>
                      {codebase.pr_only ? <V4Badge tone="gold">PR-only</V4Badge> : null}
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      <V4Badge tone="purple">Queen Maintainer</V4Badge>
                      <V4Badge tone="info">codebase_execution</V4Badge>
                      <V4Badge tone="warn">simulate-first</V4Badge>
                    </div>
                    {resolverSkills.length > 0 ? (
                      <div className="space-y-1">
                        <p className="text-[10px] font-medium uppercase tracking-wider text-(--qs-text-4)">
                          Resolved skills
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {resolverSkills.map((slug) => (
                            <ScvSkillBadge key={slug} slug={slug} />
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>

                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  <span className="text-xs text-(--qs-text-3)">
                    {formatTimeAgoIso(proposal.created_at, { nullLabel: "recent", invalidLabel: "recent" })} · {proposal.proposed_by_role}
                  </span>
                  <button
                    type="button"
                    className={cn(
                      "qs-btn qs-btn--ghost qs-btn--sm",
                      proposalBusyId === proposal.id && "opacity-60",
                    )}
                    disabled={proposalBusyId !== null || autoApproveBusy}
                    onClick={() => void onReview(proposal.id, "reject")}
                  >
                    {proposalBusyId === proposal.id ? "Working…" : "Reject"}
                  </button>
                  <button
                    type="button"
                    className={cn(
                      "qs-btn qs-btn--green qs-btn--sm",
                      proposalBusyId === proposal.id && "opacity-60",
                    )}
                    disabled={proposalBusyId !== null || autoApproveBusy}
                    onClick={() => void onReview(proposal.id, "approve")}
                  >
                    {proposalBusyId === proposal.id ? "Working…" : "Approve"}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {hiddenProposalCount > 0 && !showAllProposals ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost mt-3 w-full justify-center py-2.5 text-sm font-semibold"
            disabled={autoApproveBusy || proposalBusyId !== null || fetchAllBusy}
            onClick={() => void loadAllProposals()}
          >
            Show all ({queuePendingCount})
          </button>
        ) : null}
        {showAllProposals && queuePendingCount > SCV_PENDING_PREVIEW_LIMIT ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost mt-3 w-full justify-center py-2.5 text-sm font-semibold"
            onClick={() => setShowAllProposals(false)}
          >
            Show less
          </button>
        ) : null}
      </div>

      <div className="border-t border-(--qs-border)/50 pt-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--qs-text-3)">
            Recently approved
          </p>
          {recentBusy ? (
            <span className="inline-flex items-center gap-1 text-[10px] text-(--qs-text-4)">
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
              Loading…
            </span>
          ) : null}
        </div>
        {recentHandled.length === 0 && !recentBusy ? (
          <p className="text-xs text-(--qs-text-4)">No approved SCV proposals yet.</p>
        ) : (
          <div className="space-y-2">
            {visibleHandled.map((proposal) => (
              <div
                key={proposal.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-(--qs-border)/40 bg-black/20 px-3 py-2"
              >
                <div className="min-w-0 flex-1">
                  <div className="mb-0.5 flex flex-wrap items-center gap-2">
                    <span className="font-(family-name:--font-jetbrains-mono) text-[10px] text-(--qs-text-3)">
                      {shortProposalId(proposal.id)}
                    </span>
                    <V4Badge tone="ok">approved</V4Badge>
                    {isAutoApproved(proposal.reviewed_by_subject) ? (
                      <V4Badge tone="gold">auto</V4Badge>
                    ) : null}
                  </div>
                  <p className="line-clamp-1 text-xs font-medium text-(--qs-text)">{proposal.title}</p>
                  <p className="text-[10px] text-(--qs-text-4)">
                    {formatTimeAgoIso(proposal.reviewed_at ?? proposal.created_at, {
                      nullLabel: "recent",
                      invalidLabel: "recent",
                    })}{" "}
                    · {proposal.proposed_by_role}
                  </p>
                </div>
                {proposal.handoff_session_id ? (
                  <Link
                    href={`/agents?session=${encodeURIComponent(proposal.handoff_session_id)}`}
                    className="qs-btn qs-btn--ghost qs-btn--sm shrink-0"
                  >
                    Open session
                  </Link>
                ) : (
                  <span className="text-[10px] text-(--qs-text-4)">No Maintainer session</span>
                )}
              </div>
            ))}
          </div>
        )}
        {recentHandled.length > SCV_HANDLED_PREVIEW_LIMIT ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost mt-3 w-full justify-center py-2 text-sm"
            onClick={() => {
              if (showAllHandled) {
                setShowAllHandled(false);
                return;
              }
              void loadRecentHandled(20).then(() => setShowAllHandled(true));
            }}
          >
            {showAllHandled ? "Show less" : `Show all (${recentHandled.length})`}
          </button>
        ) : null}
      </div>
    </div>
  );
}

export const ScvPendingProposalsPanel = memo(ScvPendingProposalsPanelInner);
