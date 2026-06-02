"use client";

import { Loader2 } from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { HiveSwitch } from "@/components/ui/hive-switch";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, type V4BadgeTone } from "@/components/ui/v4";
import { HiveApiError, hivePostJson } from "@/lib/api";
import type { CodebaseLane, PendingProposal, StudioPolicy } from "@/lib/execution-studio-shared-types";
import { cn } from "@/lib/utils";

type RiskFilter = "all" | "low" | "medium" | "high";

export interface ScvPendingProposalsPanelProps {
  pendingProposals: PendingProposal[];
  pendingProposalsTotal?: number;
  policy: StudioPolicy;
  codebase: CodebaseLane;
  policyBusy: boolean;
  proposalBusyId: string | null;
  bulkDismissBusy: boolean;
  onPatchPolicy: (patch: Partial<StudioPolicy>) => Promise<void>;
  onReview: (proposalId: string, decision: "approve" | "reject") => Promise<void>;
  onDismissAll: () => Promise<void>;
  onReloadOverview: (opts?: { silent?: boolean }) => Promise<void>;
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

function formatProposalAge(createdAt: string | null | undefined): string {
  if (!createdAt) return "recent";
  const created = new Date(createdAt);
  if (Number.isNaN(created.getTime())) return "recent";
  const minutes = Math.max(1, Math.round((Date.now() - created.getTime()) / 60_000));
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours}h ago`;
  return created.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
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
  bulkDismissBusy,
  onPatchPolicy,
  onReview,
  onDismissAll,
  onReloadOverview,
}: ScvPendingProposalsPanelProps): JSX.Element {
  const [query, setQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("all");
  const [autoApproveBusy, setAutoApproveBusy] = useState(false);

  const resolverSkills = useMemo(
    () => [...codebase.agent_skills, ...codebase.agent_roles].filter(Boolean).slice(0, 8),
    [codebase.agent_roles, codebase.agent_skills],
  );

  const filteredProposals = useMemo(() => {
    const q = query.trim().toLowerCase();
    return pendingProposals.filter((proposal) => {
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
  }, [pendingProposals, query, riskFilter]);

  const autoApprovePending = useCallback(async (): Promise<void> => {
    const eligible = pendingProposals.filter((row) => row.risk_level.trim().toLowerCase() !== "high");
    if (eligible.length === 0) {
      return;
    }
    setAutoApproveBusy(true);
    try {
      const out = await hivePostJson<{ processed: number; skipped: number }>(
        "execution-studio/proposals/bulk-review",
        { decision: "approve", limit: 50 },
      );
      if (out.processed > 0) {
        await onReloadOverview({ silent: true });
        toast.success(`Auto-approved ${out.processed} SCV proposal(s).`);
      }
      if (out.skipped > 0) {
        toast.message(`${out.skipped} high-risk proposal(s) still need manual approval.`);
      }
    } catch (exc) {
      const msg = exc instanceof HiveApiError ? exc.message : "Auto-approve failed.";
      toast.error(msg);
    } finally {
      setAutoApproveBusy(false);
    }
  }, [onReloadOverview, pendingProposals]);

  useEffect(() => {
    if (!policy.codebase_auto_approve_enabled) {
      return;
    }
    const eligible = pendingProposals.filter((row) => row.risk_level.trim().toLowerCase() !== "high");
    if (eligible.length === 0) {
      return;
    }
    let cancelled = false;
    void (async () => {
      if (cancelled) return;
      await autoApprovePending();
    })();
    return () => {
      cancelled = true;
    };
  }, [autoApprovePending, pendingProposals, policy.codebase_auto_approve_enabled]);

  const patchAutoApprove = useCallback(
    async (enabled: boolean) => {
      await onPatchPolicy({ codebase_auto_approve_enabled: enabled });
      toast.success(
        enabled
          ? "Auto approve enabled — low/medium SCV proposals approve automatically."
          : "Manual mode — SCV proposals wait for your approval.",
      );
      if (enabled) {
        await autoApprovePending();
      }
    },
    [autoApprovePending, onPatchPolicy],
  );

  if (pendingProposals.length === 0) {
    return <></>;
  }

  const total = pendingProposalsTotal ?? pendingProposals.length;

  return (
    <div id="codebase-pending" className="qs-bubble shrink-0 space-y-4 p-4">
      <div>
        <p className="text-sm font-semibold text-(--qs-text)">Pending SCV proposals</p>
        <p className="mt-1 text-xs text-(--qs-text-3)">
          Research → approval → SCV / Queen Maintainer handoff. Showing {pendingProposals.length}
          {total > pendingProposals.length ? ` of ${total} total` : ""}.
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
          title="Auto approve approves low/medium SCV proposals. High-risk stays manual."
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
            {filteredProposals.length > 0 ? (
              <span className="ml-2 font-normal normal-case tracking-normal text-(--qs-text-4)">
                ({filteredProposals.length})
              </span>
            ) : null}
          </p>
          {autoApproveBusy ? (
            <span className="inline-flex items-center gap-1 text-[10px] text-(--qs-text-4)">
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
              Auto-approving…
            </span>
          ) : null}
        </div>

        <div className="v4-sessions-list-scroll hive-scrollbar">
          {filteredProposals.length === 0 ? (
            <div className="rounded-xl border border-dashed border-(--qs-border) bg-black/20 px-4 py-6 text-center">
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
            </div>
          ) : (
            filteredProposals.map((proposal) => (
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
                    {formatProposalAge(proposal.created_at)} · {proposal.proposed_by_role}
                  </span>
                  <button
                    type="button"
                    className={cn(
                      "qs-btn qs-btn--ghost qs-btn--sm",
                      proposalBusyId === proposal.id && "opacity-60",
                    )}
                    disabled={proposalBusyId !== null || bulkDismissBusy || autoApproveBusy}
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
                    disabled={proposalBusyId !== null || bulkDismissBusy || autoApproveBusy}
                    onClick={() => void onReview(proposal.id, "approve")}
                  >
                    {proposalBusyId === proposal.id ? "Working…" : "Approve"}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {filteredProposals.length > 0 ? (
          <button
            type="button"
            className="qs-btn qs-btn--danger mt-3 w-full justify-center py-2.5 text-sm font-semibold disabled:opacity-45"
            disabled={bulkDismissBusy || proposalBusyId !== null || autoApproveBusy}
            onClick={() => void onDismissAll()}
          >
            {bulkDismissBusy
              ? "Clearing…"
              : query.trim() || riskFilter !== "all"
                ? `Clear filtered (${filteredProposals.length})`
                : `Clear all (${filteredProposals.length})`}
          </button>
        ) : null}
      </div>
    </div>
  );
}

export const ScvPendingProposalsPanel = memo(ScvPendingProposalsPanelInner);
