"use client";

import { Code2, Loader2, Wrench } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useState } from "react";
import { toast } from "sonner";

import { HiveSwitch } from "@/components/ui/hive-switch";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hivePatchJson, hivePostJson } from "@/lib/api";
import type {
  CodebaseLane,
  ExecutionMode,
  PendingProposal,
  StudioPolicy,
} from "@/lib/execution-studio-shared-types";

export interface ExecutionStudioCodebaseLanePanelProps {
  codebase: CodebaseLane;
  policy: StudioPolicy;
  pendingProposals: PendingProposal[] | undefined;
  pendingProposalsTotal?: number;
  loading: boolean;
  onPolicyUpdate: (policy: StudioPolicy) => void;
  onError: (message: string | null) => void;
  onReloadOverview: (opts?: { silent?: boolean }) => Promise<void>;
  onProposalReviewed: (proposalId: string) => void;
}

function ExecutionStudioCodebaseLanePanelInner({
  codebase,
  policy,
  pendingProposals,
  pendingProposalsTotal,
  loading,
  onPolicyUpdate,
  onError,
  onReloadOverview,
  onProposalReviewed,
}: ExecutionStudioCodebaseLanePanelProps) {
  const [policyBusy, setPolicyBusy] = useState(false);
  const [maintainerBusy, setMaintainerBusy] = useState(false);
  const [proposalBusyId, setProposalBusyId] = useState<string | null>(null);
  const [bulkDismissBusy, setBulkDismissBusy] = useState(false);
  const [lastSessionId, setLastSessionId] = useState<string | null>(null);

  const patchPolicy = useCallback(
    async (patch: Partial<StudioPolicy>) => {
      setPolicyBusy(true);
      onError(null);
      try {
        const resp = await hivePatchJson<{ policy: StudioPolicy }>("execution-studio/policy", patch);
        onPolicyUpdate(resp.policy);
      } catch (exc) {
        onError(exc instanceof HiveApiError ? exc.message : "Policy update failed.");
      } finally {
        setPolicyBusy(false);
      }
    },
    [onError, onPolicyUpdate],
  );

  const reviewProposal = useCallback(
    async (proposalId: string, decision: "approve" | "reject") => {
      setProposalBusyId(proposalId);
      onError(null);
      try {
        const out = await hivePostJson<{
          handoff?: { ok?: boolean; session_id?: string; error?: string; message?: string; skipped?: boolean };
          status: string;
        }>(`execution-studio/proposals/${encodeURIComponent(proposalId)}/review`, { decision });
        onProposalReviewed(proposalId);
        if (decision === "reject") {
          toast.success("Proposal rejected.");
        } else if (out.handoff?.session_id) {
          setLastSessionId(out.handoff.session_id);
          toast.success("Approved — Queen Maintainer session queued.", {
            description: "Open session below or check Agents → Sessions.",
          });
        } else if (out.handoff?.ok === false) {
          const reason = out.handoff.error ?? out.handoff.message ?? "handoff_blocked";
          toast.message("Approved — Maintainer handoff blocked", {
            description:
              reason === "daily_limit_reached"
                ? "Daily Maintainer run limit reached. Proposal is approved; run Maintainer manually tomorrow or raise the limit in Settings."
                : String(reason),
          });
        } else {
          toast.success("Proposal approved.");
        }
        await onReloadOverview({ silent: true });
      } catch (exc) {
        const msg = exc instanceof HiveApiError ? exc.message : "Proposal review failed.";
        onError(msg);
        toast.error(msg);
      } finally {
        setProposalBusyId(null);
      }
    },
    [onError, onProposalReviewed, onReloadOverview],
  );

  const dismissAllPending = useCallback(async () => {
    const count = pendingProposals?.length ?? 0;
    if (count === 0) {
      return;
    }
    const total = pendingProposalsTotal ?? count;
    const confirmed = window.confirm(
      `Reject all ${count} proposals shown here${total > count ? ` (${total} total pending in hive)` : ""}? Duplicate auto-generated SCV handoffs can be cleared safely.`,
    );
    if (!confirmed) {
      return;
    }
    setBulkDismissBusy(true);
    onError(null);
    try {
      const out = await hivePostJson<{ processed: number; skipped: number }>(
        "execution-studio/proposals/bulk-review",
        { decision: "reject", limit: 50 },
      );
      toast.success(`Dismissed ${out.processed} proposal(s).`);
      await onReloadOverview({ silent: true });
    } catch (exc) {
      const msg = exc instanceof HiveApiError ? exc.message : "Bulk dismiss failed.";
      onError(msg);
      toast.error(msg);
    } finally {
      setBulkDismissBusy(false);
    }
  }, [onError, onReloadOverview, pendingProposals?.length, pendingProposalsTotal]);

  const runMaintainer = useCallback(async () => {
    setMaintainerBusy(true);
    onError(null);
    setLastSessionId(null);
    try {
      const out = await hivePostJson<{ session_id: string; message?: string }>(
        "execution-studio/codebase/maintainer-run",
        {},
      );
      setLastSessionId(out.session_id);
      toast.success(out.message ?? `Maintainer session ${out.session_id} queued.`);
      await onReloadOverview();
    } catch (exc) {
      const msg = exc instanceof HiveApiError ? exc.message : "Maintainer run failed.";
      onError(msg);
      toast.error(msg);
    } finally {
      setMaintainerBusy(false);
    }
  }, [onError, onReloadOverview]);

  const toggleMaintainerRoutine = useCallback(
    async (enabled: boolean) => {
      setPolicyBusy(true);
      onError(null);
      try {
        await hivePatchJson("execution-studio/codebase/routine", { enabled });
        await onReloadOverview();
      } catch (exc) {
        onError(exc instanceof HiveApiError ? exc.message : "Routine toggle failed.");
      } finally {
        setPolicyBusy(false);
      }
    },
    [onError, onReloadOverview],
  );

  return (
    <>
      {(pendingProposals?.length ?? 0) > 0 ? (
        <div id="codebase-pending" className="qs-bubble qs-bubble--tint-amber shrink-0 space-y-3 p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-(--qs-text)">Pending SCV proposals</p>
              <p className="mt-1 text-xs text-(--qs-text-3)">
                Research → approval → SCV / Queen Maintainer handoff. Showing {pendingProposals?.length ?? 0}
                {(pendingProposalsTotal ?? 0) > (pendingProposals?.length ?? 0)
                  ? ` of ${pendingProposalsTotal} total`
                  : ""}
                .
              </p>
            </div>
            {(pendingProposals?.length ?? 0) > 1 ? (
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm shrink-0"
                disabled={bulkDismissBusy || proposalBusyId !== null}
                onClick={() => void dismissAllPending()}
              >
                {bulkDismissBusy ? "Dismissing…" : "Dismiss all shown"}
              </button>
            ) : null}
          </div>
          <div className="space-y-2">
            {pendingProposals?.map((proposal) => (
              <article key={proposal.id} className="qs-bubble-inner flex flex-col gap-3 p-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-(--qs-text)">{proposal.title}</p>
                  <p className="mt-1 text-xs text-(--qs-text-3)">{proposal.goal_excerpt || proposal.description}</p>
                  <p className="mt-1 font-mono text-[10px] text-(--qs-text-4)">
                    {proposal.proposed_by_role} · {proposal.risk_level}
                  </p>
                </div>
                <div className="v4-dream-cycle-card-actions">
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    disabled={proposalBusyId !== null}
                    onClick={() => void reviewProposal(proposal.id, "reject")}
                  >
                    {proposalBusyId === proposal.id ? "Working…" : "Reject"}
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm"
                    disabled={proposalBusyId !== null}
                    onClick={() => void reviewProposal(proposal.id, "approve")}
                  >
                    {proposalBusyId === proposal.id ? "Working…" : "Approve"}
                  </button>
                </div>
              </article>
            ))}
          </div>
        </div>
      ) : null}

      <div className="qs-bubble qs-bubble--tint-cyan shrink-0 space-y-3 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="flex items-center gap-2 text-sm font-semibold text-(--qs-text)">
              <Code2 className="h-4 w-4 text-cyan" aria-hidden />
              SCV — internal codebase lane
            </p>
            <p className="mt-1 text-xs text-(--qs-text-3)">
              Research → approval → Queen Maintainer handoff. Economy models, simulate-first, PR-only.
            </p>
          </div>
          <V4Badge tone={codebase.queen_maintainer_enabled ? "ok" : "warn"}>
            {codebase.queen_maintainer_enabled ? "Maintainer ON" : "Maintainer flag off"}
          </V4Badge>
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <article className="qs-bubble-inner p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-4)">Tech health</p>
            <p className="mt-1 font-mono text-xl text-cyan">
              {typeof codebase.tech_health.health_score === "number"
                ? codebase.tech_health.health_score.toFixed(2)
                : "—"}
            </p>
            <p className="mt-1 text-[10px] text-(--qs-text-3)">
              {codebase.tech_health.signals.length
                ? codebase.tech_health.signals.join(", ")
                : "No critical signals"}
            </p>
          </article>
          <article className="qs-bubble-inner p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-4)">GitHub target</p>
            <p className="mt-1 text-xs text-(--qs-text-2)">
              {codebase.github_repo.configured
                ? `${codebase.github_repo.owner}/${codebase.github_repo.repo}`
                : "Set QUEEN_MAINTAINER_GITHUB_OWNER/REPO"}
            </p>
            <p className="mt-1 text-[10px] text-(--qs-text-3)">
              Connector:{" "}
              {codebase.repo_connector?.status === "active"
                ? codebase.repo_connector.display_name
                : "install & activate github_rest"}
            </p>
          </article>
          <article className="qs-bubble-inner p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-4)">Agent stack</p>
            <p className="mt-1 text-xs text-(--qs-text-2)">{codebase.agent_roles.join(" · ")}</p>
            <p className="mt-1 font-mono text-[10px] text-(--qs-text-4)">
              {codebase.agent_skills.slice(0, 3).join(", ")}
            </p>
          </article>
          {codebase.budget ? (
            <article className="qs-bubble-inner qs-bubble--tint-amber p-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-pollen">Budget guard</p>
              <p className="mt-1 font-mono text-sm text-(--qs-text)">
                ${codebase.budget.session_cap_usd.toFixed(2)} / session
              </p>
              <p className="mt-1 text-[10px] text-(--qs-text-3)">
                Runs today: {codebase.budget.runs_today}/{codebase.budget.daily_run_limit}
                {codebase.budget.remaining_runs_today <= 0 ? " · limit reached" : ""}
              </p>
              <p className="mt-1 font-mono text-[9px] text-(--qs-text-4)">
                {codebase.budget.routing_mode} · {codebase.budget.models.coder ?? "mini"}
              </p>
            </article>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-(--qs-text-2)">
            <HiveSwitch
              checked={codebase.maintainer_routine.enabled}
              disabled={policyBusy || !codebase.queen_maintainer_enabled}
              onCheckedChange={(checked) => void toggleMaintainerRoutine(checked)}
            />
            Weekly routine
          </label>
          <QsSelect
            className="min-w-44"
            value={policy.codebase_default_mode ?? "simulate"}
            disabled={policyBusy || loading}
            onValueChange={(next) => void patchPolicy({ codebase_default_mode: next as ExecutionMode })}
            options={[
              { value: "draft", label: "Codebase: Draft" },
              { value: "simulate", label: "Codebase: Simulate" },
              { value: "live", label: "Codebase: Live PR" },
            ]}
          />
          <label className="flex items-center gap-2 text-xs text-(--qs-text-2)">
            <HiveSwitch
              checked={policy.live_codebase_requires_approval ?? true}
              disabled={policyBusy || loading}
              onCheckedChange={(checked) => void patchPolicy({ live_codebase_requires_approval: checked })}
            />
            Approve live PRs
          </label>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm gap-2"
            disabled={
              maintainerBusy
              || !codebase.queen_maintainer_enabled
              || (codebase.budget?.remaining_runs_today ?? 1) <= 0
            }
            onClick={() => void runMaintainer()}
          >
            {maintainerBusy ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <Wrench className="h-4 w-4" aria-hidden />
            )}
            Run Queen Maintainer
          </button>
          {lastSessionId ? (
            <Link href={`/agents?session=${encodeURIComponent(lastSessionId)}`} className="qs-btn qs-btn--ghost qs-btn--sm">
              Open session
            </Link>
          ) : null}
        </div>

        <details className="text-xs text-(--qs-text-3)">
          <summary className="cursor-pointer text-(--qs-text-2)">Setup guide & denylist</summary>
          <ol className="mt-2 space-y-2 pl-4">
            {codebase.setup_steps.map((step) => (
              <li key={step.id}>
                <span className="font-semibold text-(--qs-text)">{step.title}</span>
                <span className="mt-0.5 block">{step.detail}</span>
              </li>
            ))}
          </ol>
          <p className="mt-3 font-mono text-[10px] text-(--qs-text-4)">
            Denylist: {codebase.denylist_prefixes.slice(0, 6).join(", ")}…
          </p>
        </details>
      </div>
    </>
  );
}

export const ExecutionStudioCodebaseLanePanel = memo(ExecutionStudioCodebaseLanePanelInner);
