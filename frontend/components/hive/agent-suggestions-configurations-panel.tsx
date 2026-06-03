"use client";

import { Check, ExternalLink, X } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { ForagerProgressCell } from "@/components/hive/forager-progress-cell";
import { HiveSwitch } from "@/components/ui/hive-switch";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, type V4BadgeTone } from "@/components/ui/v4";
import { HiveApiError, hivePatchJson } from "@/lib/api";
import { formatTimeAgoIso } from "@/lib/format-relative-time";
import type { AgentInitiativePolicy, AgentSuggestionRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type RiskFilter = "all" | "low" | "medium" | "high";

const SUGGESTION_PREVIEW_LIMIT = 3;

export interface AgentSuggestionsConfigurationsPanelProps {
  rows: AgentSuggestionRow[];
  policy: AgentInitiativePolicy;
  busyId: string | null;
  bulkBusy: boolean;
  policyBusy: boolean;
  onPolicyChange: (policy: AgentInitiativePolicy) => void;
  onReload: () => Promise<void>;
  onReview: (id: string, decision: "approve" | "reject") => Promise<void>;
  onApproveAll: (includeHighRisk: boolean) => Promise<void>;
  onRejectAll: () => Promise<void>;
}

function shortProposalId(id: string): string {
  return `S-${id.replace(/-/g, "").slice(0, 4).toUpperCase()}`;
}

function riskTone(risk: string): V4BadgeTone {
  const normalized = risk.trim().toLowerCase();
  if (normalized === "low") return "ok";
  if (normalized === "high") return "gold";
  return "warn";
}

function SuggestionSkillBadge({ slug }: { slug: string }): JSX.Element {
  return (
    <span className="inline-flex max-w-full items-center rounded-md border border-pollen/45 bg-pollen/10 px-2 py-0.5 font-(family-name:--font-jetbrains-mono) text-[10px] text-pollen">
      {slug}
    </span>
  );
}

function AgentSuggestionsConfigurationsPanelInner({
  rows,
  policy,
  busyId,
  bulkBusy,
  policyBusy,
  onPolicyChange,
  onReload,
  onReview,
  onApproveAll,
  onRejectAll,
}: AgentSuggestionsConfigurationsPanelProps): JSX.Element {
  const [query, setQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("all");
  const [showAllRows, setShowAllRows] = useState(false);
  const [autoApproveBusy, setAutoApproveBusy] = useState(false);
  const [rejectAllBusy, setRejectAllBusy] = useState(false);

  const pendingRows = useMemo(() => rows.filter((row) => row.status === "pending"), [rows]);

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return pendingRows.filter((row) => {
      if (riskFilter !== "all" && row.risk_level.trim().toLowerCase() !== riskFilter) {
        return false;
      }
      if (!q) return true;
      const haystack = [
        row.title,
        row.description,
        row.proposed_by_role,
        row.proposal_type,
        row.risk_level,
        row.evaluation_reason ?? "",
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [pendingRows, query, riskFilter]);

  const visibleRows = useMemo(() => {
    if (showAllRows) {
      return filteredRows;
    }
    return filteredRows.slice(0, SUGGESTION_PREVIEW_LIMIT);
  }, [filteredRows, showAllRows]);

  const hiddenRowCount = Math.max(0, filteredRows.length - SUGGESTION_PREVIEW_LIMIT);
  const highRiskPending = pendingRows.filter((row) => row.risk_level === "high").length;

  useEffect(() => {
    setShowAllRows(false);
  }, [query, riskFilter, pendingRows.length]);

  const patchAutoApprove = useCallback(
    async (enabled: boolean) => {
      setAutoApproveBusy(true);
      try {
        const updated = await hivePatchJson<AgentInitiativePolicy>("agents/suggestions/policy", {
          auto_approve_enabled: enabled,
        });
        onPolicyChange(updated);
        await onReload();
        toast.success(
          enabled
            ? "Auto approve enabled — eligible suggestions approve without manual confirm."
            : "Manual mode — each suggestion waits for your approval.",
        );
      } catch (exc) {
        const msg = exc instanceof HiveApiError ? exc.message : "Policy update failed.";
        toast.error(msg);
      } finally {
        setAutoApproveBusy(false);
      }
    },
    [onPolicyChange, onReload],
  );

  const patchIncludeHighRisk = useCallback(
    async (enabled: boolean) => {
      setAutoApproveBusy(true);
      try {
        const updated = await hivePatchJson<AgentInitiativePolicy>("agents/suggestions/policy", {
          include_high_risk: enabled,
        });
        onPolicyChange(updated);
        await onReload();
        toast.success(enabled ? "High-risk items included in auto approve." : "High-risk items require manual approve.");
      } catch (exc) {
        toast.error(exc instanceof HiveApiError ? exc.message : "Policy update failed.");
      } finally {
        setAutoApproveBusy(false);
      }
    },
    [onPolicyChange, onReload],
  );

  const rejectAllVisible = useCallback(async () => {
    if (filteredRows.length === 0) {
      return;
    }
    const confirmed = window.confirm(
      `Reject ${filteredRows.length} suggestion${filteredRows.length === 1 ? "" : "s"} shown here?`,
    );
    if (!confirmed) {
      return;
    }
    setRejectAllBusy(true);
    try {
      await onRejectAll();
    } finally {
      setRejectAllBusy(false);
    }
  }, [filteredRows.length, onRejectAll]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-stretch">
        <input
          className="qs-input min-w-0 flex-1"
          placeholder="Filter suggestions by title / role / risk / type…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <label
          className="flex shrink-0 items-center justify-between gap-2 rounded-lg border border-pollen/35 bg-black/25 px-3 py-2 text-xs text-(--qs-text-2) md:min-w-[11.5rem]"
          title="Auto approve applies initiative suggestions without manual confirm (SCV codebase excluded)."
        >
          <span className="whitespace-nowrap font-medium lowercase">
            {policy.auto_approve_enabled ? "auto approve" : "manual"}
          </span>
          <HiveSwitch
            checked={Boolean(policy.auto_approve_enabled)}
            disabled={policyBusy || autoApproveBusy || bulkBusy}
            aria-label="Toggle auto approve for agent suggestions"
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

      {policy.auto_approve_enabled ? (
        <div className="flex flex-wrap items-center gap-3 text-xs text-(--qs-text-3)">
          <span className="text-pollen">Auto approve is ON</span>
          <label className="inline-flex items-center gap-2">
            <HiveSwitch
              checked={Boolean(policy.include_high_risk)}
              disabled={policyBusy || autoApproveBusy || bulkBusy}
              aria-label="Include high risk in auto approve"
              onCheckedChange={(checked) => void patchIncludeHighRisk(checked)}
            />
            Include high risk
          </label>
        </div>
      ) : null}

      <div>
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--qs-text-3)">
            Proposals
            {filteredRows.length > 0 ? (
              <span className="ml-2 font-normal normal-case tracking-normal text-(--qs-text-4)">
                ({filteredRows.length})
              </span>
            ) : null}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <V4Badge tone="purple">{pendingRows.length} pending</V4Badge>
            {highRiskPending > 0 ? <V4Badge tone="gold">{highRiskPending} high risk</V4Badge> : null}
          </div>
        </div>

        <div className="v4-sessions-list-scroll hive-scrollbar">
          {filteredRows.length === 0 ? (
            <div className="rounded-xl border border-dashed border-pollen/35 bg-black/20 px-4 py-6 text-center">
              <p className="text-sm text-(--qs-text-2)">
                {pendingRows.length === 0
                  ? policy.auto_approve_enabled
                    ? "No pending suggestions — auto approve cleared the queue."
                    : "No pending suggestions — agents propose after reflection cycles."
                  : "No suggestions match this filter."}
              </p>
              {pendingRows.length > 0 ? (
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
              ) : null}
            </div>
          ) : (
            visibleRows.map((row) => {
              const routeTags = [
                row.proposed_by_role,
                row.proposal_type.replace(/_/g, " "),
                row.risk_level,
                policy.auto_approve_enabled ? "auto-approve" : "manual-approve",
              ];
              const nodeTags = [
                row.evaluation_reason?.split(":")[0] ?? "initiative",
                row.requires_manual_approval ? "review-required" : "auto-eligible",
              ].filter(Boolean);
              const impactPct = Math.round(Math.max(0, Math.min(1, row.impact_score)) * 100);
              const sessionHref = row.supervisor_session_id
                ? `/agents?session=${encodeURIComponent(row.supervisor_session_id)}`
                : null;

              return (
                <div key={row.id} className="v4-session-row v4-session-row--pollen">
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex flex-wrap items-center gap-2">
                      <span className="font-(family-name:--font-jetbrains-mono) text-[11px] text-(--qs-text-3)">
                        {shortProposalId(row.id)}
                      </span>
                      <V4Badge tone="warn">pending</V4Badge>
                      <V4Badge tone={riskTone(row.risk_level)}>{row.risk_level}</V4Badge>
                      <V4Badge tone="purple">{row.proposed_by_role}</V4Badge>
                    </div>
                    <p className="v4-session-goal text-sm font-medium text-(--qs-text)" title={row.title}>
                      {row.title}
                    </p>
                    <p className="mt-1 line-clamp-2 text-xs text-(--qs-text-3)">{row.description}</p>

                    <div className="mt-2 space-y-1.5" data-testid="agent-suggestion-pattern-skills">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-3)">
                          Source routes
                        </p>
                        <V4Badge tone="gold">initiative-v1</V4Badge>
                        {row.risk_level === "high" ? <V4Badge tone="gold">high risk</V4Badge> : null}
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {routeTags.map((tag) => (
                          <V4Badge key={`${row.id}-route-${tag}`} tone="info">
                            {tag}
                          </V4Badge>
                        ))}
                      </div>
                      <div className="space-y-1">
                        <p className="text-[10px] font-medium uppercase tracking-wider text-(--qs-text-4)">
                          Node routes
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {nodeTags.map((tag) => (
                            <SuggestionSkillBadge key={`${row.id}-node-${tag}`} slug={tag} />
                          ))}
                        </div>
                      </div>
                      <ForagerProgressCell
                        pct={impactPct}
                        detail={`Impact score ${impactPct}% · ${row.proposal_type.replace(/_/g, " ")}`}
                        href={sessionHref}
                      />
                    </div>
                  </div>

                  <div className="flex shrink-0 flex-wrap items-center gap-2">
                    <span className="text-xs text-(--qs-text-3)">
                      {formatTimeAgoIso(row.created_at, { nullLabel: "recent", invalidLabel: "recent" })} · impact{" "}
                      {impactPct}%
                    </span>
                    {sessionHref ? (
                      <Link href={sessionHref} className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5">
                        <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                        Session
                      </Link>
                    ) : null}
                    <button
                      type="button"
                      className={cn("qs-btn qs-btn--green qs-btn--sm gap-1.5", busyId === row.id && "opacity-60")}
                      disabled={busyId !== null || bulkBusy}
                      onClick={() => void onReview(row.id, "approve")}
                    >
                      <Check className="h-3.5 w-3.5" aria-hidden />
                      Approve
                    </button>
                    <button
                      type="button"
                      className={cn(
                        "qs-btn qs-btn--danger qs-btn--sm gap-1.5",
                        busyId === row.id && "opacity-60",
                      )}
                      disabled={busyId !== null || bulkBusy}
                      onClick={() => void onReview(row.id, "reject")}
                    >
                      <X className="h-3.5 w-3.5" aria-hidden />
                      Reject
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {hiddenRowCount > 0 && !showAllRows ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost mt-3 w-full justify-center py-2.5 text-sm font-semibold"
            disabled={rejectAllBusy || busyId !== null || bulkBusy}
            onClick={() => setShowAllRows(true)}
          >
            Show all ({filteredRows.length})
          </button>
        ) : null}
        {showAllRows && filteredRows.length > SUGGESTION_PREVIEW_LIMIT ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost mt-3 w-full justify-center py-2.5 text-sm font-semibold"
            onClick={() => setShowAllRows(false)}
          >
            Show less
          </button>
        ) : null}

        {filteredRows.length > 0 && !policy.auto_approve_enabled ? (
          <>
            <button
              type="button"
              className="qs-btn qs-btn--primary mt-3 w-full justify-center py-2.5 text-sm font-semibold disabled:opacity-45"
              disabled={busyId !== null || bulkBusy}
              onClick={() => void onApproveAll(false)}
            >
              {bulkBusy ? "Approving…" : `Approve all (${filteredRows.length})`}
            </button>
            {highRiskPending > 0 ? (
              <button
                type="button"
                className="qs-btn qs-btn--ghost mt-2 w-full justify-center py-2 text-sm"
                disabled={busyId !== null || bulkBusy}
                onClick={() => void onApproveAll(true)}
              >
                Approve all including {highRiskPending} high-risk
              </button>
            ) : null}
          </>
        ) : null}

        {filteredRows.length > 0 ? (
          <button
            type="button"
            className="qs-btn qs-btn--danger mt-3 w-full justify-center py-2.5 text-sm font-semibold disabled:opacity-45"
            disabled={rejectAllBusy || busyId !== null || bulkBusy}
            onClick={() => void rejectAllVisible()}
          >
            {rejectAllBusy
              ? "Rejecting…"
              : query.trim() || riskFilter !== "all"
                ? `Reject filtered (${filteredRows.length})`
                : `Reject all (${filteredRows.length})`}
          </button>
        ) : null}
      </div>
    </div>
  );
}

export const AgentSuggestionsConfigurationsPanel = memo(AgentSuggestionsConfigurationsPanelInner);
