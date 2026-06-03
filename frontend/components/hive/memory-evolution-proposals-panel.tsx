"use client";

import { Check, X } from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { ForagerProgressCell } from "@/components/hive/forager-progress-cell";
import { HiveSwitch } from "@/components/ui/hive-switch";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, type V4BadgeTone } from "@/components/ui/v4";
import { HiveApiError, hivePatchJson } from "@/lib/api";
import { formatTimeAgoIso } from "@/lib/format-relative-time";
import type { MemoryEvolutionPolicy, MemoryEvolutionProposalRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type KindFilter = "all" | string;

const PROPOSAL_PREVIEW_LIMIT = 3;
const HIGH_IMPORTANCE_THRESHOLD = 0.82;

export interface MemoryEvolutionProposalsPanelProps {
  rows: MemoryEvolutionProposalRow[];
  policy: MemoryEvolutionPolicy;
  busyId: string | null;
  bulkBusy: boolean;
  policyBusy: boolean;
  onPolicyChange: (policy: MemoryEvolutionPolicy) => void;
  onReload: () => Promise<void>;
  onReview: (id: string, decision: "approve" | "reject") => Promise<void>;
  onApproveAll: (includeHighImportance: boolean) => Promise<void>;
  onClearAll: () => Promise<void>;
}

function shortProposalId(id: string): string {
  return `M-${id.replace(/-/g, "").slice(0, 4).toUpperCase()}`;
}

function importanceTone(score: number): V4BadgeTone {
  if (score >= HIGH_IMPORTANCE_THRESHOLD) return "gold";
  if (score >= 0.55) return "warn";
  return "ok";
}

function proposalPayloadMeta(payload: Record<string, unknown>): string {
  const parts: string[] = [];
  for (const key of [
    "sessions",
    "completion_rate",
    "failure_rate",
    "avg_strategy_score",
    "swarm_entries",
    "history_consolidations",
  ]) {
    const value = payload[key];
    if (value == null || value === "") continue;
    if (typeof value === "number") {
      parts.push(`${key}=${value.toFixed(3)}`);
    } else {
      parts.push(`${key}=${String(value)}`);
    }
  }
  return parts.join(" · ");
}

function ProposalSkillBadge({ slug }: { slug: string }): JSX.Element {
  return (
    <span className="inline-flex max-w-full items-center rounded-md border border-pollen/45 bg-pollen/10 px-2 py-0.5 font-(family-name:--font-jetbrains-mono) text-[10px] text-pollen">
      {slug}
    </span>
  );
}

function MemoryEvolutionProposalsPanelInner({
  rows,
  policy,
  busyId,
  bulkBusy,
  policyBusy,
  onPolicyChange,
  onReload,
  onReview,
  onApproveAll,
  onClearAll,
}: MemoryEvolutionProposalsPanelProps): JSX.Element {
  const [query, setQuery] = useState("");
  const [kindFilter, setKindFilter] = useState<KindFilter>("all");
  const [showAllRows, setShowAllRows] = useState(false);
  const [autoApproveBusy, setAutoApproveBusy] = useState(false);
  const [clearAllBusy, setClearAllBusy] = useState(false);

  const pendingRows = useMemo(() => rows.filter((row) => row.status === "pending"), [rows]);

  const kindOptions = useMemo(() => {
    const kinds = [...new Set(pendingRows.map((row) => row.proposal_kind.trim()).filter(Boolean))].sort();
    return [{ value: "all", label: "all kinds" }, ...kinds.map((kind) => ({ value: kind, label: kind.replace(/_/g, " ") }))];
  }, [pendingRows]);

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return pendingRows.filter((row) => {
      if (kindFilter !== "all" && row.proposal_kind !== kindFilter) {
        return false;
      }
      if (!q) return true;
      const haystack = [
        row.title,
        row.summary,
        row.proposal_kind,
        proposalPayloadMeta(row.payload ?? {}),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [kindFilter, pendingRows, query]);

  const visibleRows = useMemo(() => {
    if (showAllRows) {
      return filteredRows;
    }
    return filteredRows.slice(0, PROPOSAL_PREVIEW_LIMIT);
  }, [filteredRows, showAllRows]);

  const hiddenRowCount = Math.max(0, filteredRows.length - PROPOSAL_PREVIEW_LIMIT);
  const highImportancePending = pendingRows.filter(
    (row) => row.importance_score >= HIGH_IMPORTANCE_THRESHOLD,
  ).length;

  useEffect(() => {
    setShowAllRows(false);
  }, [query, kindFilter, pendingRows.length]);

  const patchAutoApprove = useCallback(
    async (enabled: boolean) => {
      setAutoApproveBusy(true);
      try {
        const updated = await hivePatchJson<MemoryEvolutionPolicy>("hive-mind/memory-evolution/policy", {
          auto_approve_enabled: enabled,
        });
        onPolicyChange(updated);
        await onReload();
        toast.success(
          enabled
            ? "Auto approve enabled — eligible graph edits commit without manual confirm."
            : "Manual mode — each proposal waits for your approval.",
        );
      } catch (exc) {
        toast.error(exc instanceof HiveApiError ? exc.message : "Policy update failed.");
      } finally {
        setAutoApproveBusy(false);
      }
    },
    [onPolicyChange, onReload],
  );

  const patchIncludeHighImportance = useCallback(
    async (enabled: boolean) => {
      setAutoApproveBusy(true);
      try {
        const updated = await hivePatchJson<MemoryEvolutionPolicy>("hive-mind/memory-evolution/policy", {
          include_high_importance: enabled,
        });
        onPolicyChange(updated);
        await onReload();
        toast.success(
          enabled
            ? "High-importance proposals included in auto approve."
            : "High-importance proposals require manual approve.",
        );
      } catch (exc) {
        toast.error(exc instanceof HiveApiError ? exc.message : "Policy update failed.");
      } finally {
        setAutoApproveBusy(false);
      }
    },
    [onPolicyChange, onReload],
  );

  const clearAllVisible = useCallback(async () => {
    if (filteredRows.length === 0) {
      return;
    }
    const confirmed = window.confirm(
      `Clear ${filteredRows.length} proposal${filteredRows.length === 1 ? "" : "s"} (reject without applying)?`,
    );
    if (!confirmed) {
      return;
    }
    setClearAllBusy(true);
    try {
      await onClearAll();
    } finally {
      setClearAllBusy(false);
    }
  }, [filteredRows.length, onClearAll]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-stretch">
        <input
          className="qs-input min-w-0 flex-1"
          placeholder="Filter proposals by title / kind / summary…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <label
          className="flex shrink-0 items-center justify-between gap-2 rounded-lg border border-pollen/35 bg-black/25 px-3 py-2 text-xs text-(--qs-text-2) md:min-w-[11.5rem]"
          title="Auto approve commits eligible graph edits without manual confirm."
        >
          <span className="whitespace-nowrap font-medium lowercase">
            {policy.auto_approve_enabled ? "auto approve" : "manual"}
          </span>
          <HiveSwitch
            checked={Boolean(policy.auto_approve_enabled)}
            disabled={policyBusy || autoApproveBusy || bulkBusy}
            aria-label="Toggle auto approve for memory evolution proposals"
            onCheckedChange={(checked) => void patchAutoApprove(checked)}
          />
        </label>
        <QsSelect
          className="w-full min-w-0 md:w-40 md:shrink-0"
          value={kindFilter}
          onValueChange={(next) => setKindFilter(next)}
          options={kindOptions}
        />
      </div>

      {policy.auto_approve_enabled ? (
        <div className="space-y-1">
          <p className="text-xs text-pollen">
            Auto approve is ON — eligible proposals leave the queue automatically. High-importance graph edits stay
            manual unless included below.
          </p>
          <label className="inline-flex items-center gap-2 text-xs text-(--qs-text-3)">
            <HiveSwitch
              checked={Boolean(policy.include_high_importance)}
              disabled={policyBusy || autoApproveBusy || bulkBusy}
              aria-label="Include high importance in auto approve"
              onCheckedChange={(checked) => void patchIncludeHighImportance(checked)}
            />
            Include high importance
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
            {highImportancePending > 0 ? (
              <V4Badge tone="gold">{highImportancePending} high importance</V4Badge>
            ) : null}
          </div>
        </div>

        <div className="v4-sessions-list-scroll hive-scrollbar">
          {filteredRows.length === 0 ? (
            <div className="rounded-xl border border-dashed border-pollen/35 bg-black/20 px-4 py-6 text-center">
              <p className="text-sm text-(--qs-text-2)">
                {pendingRows.length === 0
                  ? policy.auto_approve_enabled
                    ? "No pending proposals — auto approve cleared the queue."
                    : "No pending proposals — reflection cycles will surface graph edits here."
                  : "No proposals match this filter."}
              </p>
              {pendingRows.length > 0 ? (
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm mt-3"
                  onClick={() => {
                    setQuery("");
                    setKindFilter("all");
                  }}
                >
                  Reset filters
                </button>
              ) : null}
            </div>
          ) : (
            visibleRows.map((row) => {
              const payload = row.payload ?? {};
              const routeTags = [
                row.proposal_kind.replace(/_/g, " "),
                row.importance_score >= HIGH_IMPORTANCE_THRESHOLD ? "high importance" : "routine",
                policy.auto_approve_enabled ? "auto-approve" : "manual-approve",
              ];
              const nodeTags = [
                ...new Set(
                  (Array.isArray(payload.tags) ? payload.tags : [])
                    .map((tag) => String(tag).trim())
                    .filter(Boolean),
                ),
              ].slice(0, 8);
              const payloadMeta = proposalPayloadMeta(payload);
              const progressPct = Math.round(Math.max(0, Math.min(100, row.importance_score * 100)));

              return (
                <div key={row.id} className="v4-session-row v4-session-row--pollen">
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex flex-wrap items-center gap-2">
                      <span className="font-(family-name:--font-jetbrains-mono) text-[11px] text-(--qs-text-3)">
                        {shortProposalId(row.id)}
                      </span>
                      <V4Badge tone="info">pending</V4Badge>
                      <V4Badge tone={importanceTone(row.importance_score)}>
                        confidence {row.importance_score.toFixed(2)}
                      </V4Badge>
                    </div>
                    <p className="v4-session-goal text-sm font-medium text-(--qs-text)" title={row.title}>
                      {row.title || row.summary}
                    </p>
                    <p className="mt-1 line-clamp-2 text-xs text-(--qs-text-3)">
                      {row.summary !== row.title ? row.summary : null}
                      {row.summary !== row.title && payloadMeta ? " · " : ""}
                      {payloadMeta || `kind ${row.proposal_kind}`}
                    </p>

                    <div className="mt-2 space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-3)">
                          Source routes
                        </p>
                        <V4Badge tone="gold">memory-evolution</V4Badge>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {routeTags.map((tag) => (
                          <V4Badge key={`${row.id}-route-${tag}`} tone="info">
                            {tag}
                          </V4Badge>
                        ))}
                      </div>
                      {nodeTags.length > 0 ? (
                        <div className="space-y-1">
                          <p className="text-[10px] font-medium uppercase tracking-wider text-(--qs-text-4)">
                            Graph tags
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {nodeTags.map((slug) => (
                              <ProposalSkillBadge key={`${row.id}-${slug}`} slug={slug} />
                            ))}
                          </div>
                        </div>
                      ) : null}
                      <ForagerProgressCell
                        pct={progressPct}
                        detail={`Importance ${row.importance_score.toFixed(2)} · ${row.requires_manual_approval ? "manual review" : "auto-eligible"}`}
                      />
                    </div>
                  </div>

                  <div className="flex shrink-0 flex-wrap items-center gap-2">
                    <span className="text-xs text-(--qs-text-3)">
                      {formatTimeAgoIso(row.created_at) ?? "just now"}
                    </span>
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                      disabled={busyId !== null || bulkBusy || policy.auto_approve_enabled}
                      title={policy.auto_approve_enabled ? "Auto approve is handling the queue." : undefined}
                      onClick={() => void onReview(row.id, "reject")}
                    >
                      <X className="h-3.5 w-3.5" aria-hidden />
                      Reject
                    </button>
                    <button
                      type="button"
                      className={cn("qs-btn qs-btn--primary qs-btn--sm gap-1.5")}
                      disabled={busyId !== null || bulkBusy || policy.auto_approve_enabled}
                      title={policy.auto_approve_enabled ? "Auto approve is handling the queue." : undefined}
                      onClick={() => void onReview(row.id, "approve")}
                    >
                      <Check className="h-3.5 w-3.5" aria-hidden />
                      Approve
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
            disabled={clearAllBusy || busyId !== null || bulkBusy}
            onClick={() => setShowAllRows(true)}
          >
            Show all ({filteredRows.length})
          </button>
        ) : null}
        {showAllRows && filteredRows.length > PROPOSAL_PREVIEW_LIMIT ? (
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
            {highImportancePending > 0 ? (
              <button
                type="button"
                className="qs-btn qs-btn--ghost mt-2 w-full justify-center py-2 text-sm"
                disabled={busyId !== null || bulkBusy}
                onClick={() => void onApproveAll(true)}
              >
                Approve all including {highImportancePending} high-importance
              </button>
            ) : null}
          </>
        ) : null}

        {filteredRows.length > 0 ? (
          <button
            type="button"
            className="qs-btn qs-btn--danger mt-3 w-full justify-center py-2.5 text-sm font-semibold disabled:opacity-45"
            disabled={clearAllBusy || busyId !== null || bulkBusy}
            onClick={() => void clearAllVisible()}
          >
            {clearAllBusy
              ? "Clearing…"
              : query.trim() || kindFilter !== "all"
                ? `Clear filtered (${filteredRows.length})`
                : `Clear all (${filteredRows.length})`}
          </button>
        ) : null}
      </div>
    </div>
  );
}

export const MemoryEvolutionProposalsPanel = memo(MemoryEvolutionProposalsPanelInner);
