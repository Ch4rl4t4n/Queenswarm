"use client";

import { ExternalLink, FileText, Loader2 } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { PublishPackDetailModal } from "@/components/connectors/publish-pack-detail-modal";
import { PublishMediaMissingBadge } from "@/components/connectors/publish-media-preview";
import { ForagerProgressCell } from "@/components/hive/forager-progress-cell";
import { HiveSwitch } from "@/components/ui/hive-switch";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, type V4BadgeTone } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import { formatTimeAgoIso } from "@/lib/format-relative-time";
import type { PublishQueueItem, PublishQueuePolicy, PublishQueueSnapshot } from "@/lib/publish-queue-types";
import { cn } from "@/lib/utils";

export type { PublishQueueItem, PublishQueueSnapshot } from "@/lib/publish-queue-types";

export interface ExecutionStudioPublishQueuePanelProps {
  onError: (message: string | null) => void;
}

type StatusFilter = "all" | PublishQueueItem["status"];

const PACK_PREVIEW_LIMIT = 3;

function shortPackId(id: string): string {
  return `P-${id.replace(/-/g, "").slice(0, 4).toUpperCase()}`;
}

function statusTone(status: PublishQueueItem["status"]): V4BadgeTone {
  if (status === "approved") return "ok";
  if (status === "rejected") return "err";
  return "warn";
}

function packProgressPct(status: PublishQueueItem["status"]): number {
  if (status === "approved") return 100;
  if (status === "rejected") return 0;
  return 45;
}

function PackSkillBadge({ slug }: { slug: string }): JSX.Element {
  return (
    <span className="inline-flex max-w-full items-center rounded-md border border-pollen/45 bg-pollen/10 px-2 py-0.5 font-(family-name:--font-jetbrains-mono) text-[10px] text-pollen">
      {slug}
    </span>
  );
}

function ExecutionStudioPublishQueuePanelInner({ onError }: ExecutionStudioPublishQueuePanelProps) {
  const [snapshot, setSnapshot] = useState<PublishQueueSnapshot | null>(null);
  const [policy, setPolicy] = useState<PublishQueuePolicy>({ auto_approve_enabled: false });
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [policyBusy, setPolicyBusy] = useState(false);
  const [clearAllBusy, setClearAllBusy] = useState(false);
  const [detailItem, setDetailItem] = useState<PublishQueueItem | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [showAllRows, setShowAllRows] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      const data = await hiveGet<PublishQueueSnapshot>("publish-queue");
      setSnapshot(data);
      setPolicy({ auto_approve_enabled: Boolean(data.auto_approve_enabled) });
      setDetailItem((prev) => {
        if (!prev) return null;
        return data.items.find((row) => row.id === prev.id) ?? null;
      });
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Failed to load publish queue.");
    } finally {
      setLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    void load();
  }, [load]);

  const filteredRows = useMemo(() => {
    const items = snapshot?.items ?? [];
    const q = query.trim().toLowerCase();
    return items.filter((row) => {
      if (statusFilter !== "all" && row.status !== statusFilter) {
        return false;
      }
      if (!q) return true;
      const haystack = [
        row.title,
        row.body_preview,
        row.channel,
        row.status,
        row.cta,
        ...row.tags,
        ...row.hashtags,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [query, snapshot?.items, statusFilter]);

  const visibleRows = useMemo(() => {
    if (showAllRows) {
      return filteredRows;
    }
    return filteredRows.slice(0, PACK_PREVIEW_LIMIT);
  }, [filteredRows, showAllRows]);

  const hiddenRowCount = Math.max(0, filteredRows.length - PACK_PREVIEW_LIMIT);
  const pendingRows = useMemo(
    () => (snapshot?.items ?? []).filter((row) => row.status === "pending"),
    [snapshot?.items],
  );

  useEffect(() => {
    setShowAllRows(false);
  }, [query, statusFilter, snapshot?.items.length]);

  const patchAutoApprove = useCallback(
    async (enabled: boolean) => {
      setPolicyBusy(true);
      try {
        const updated = await hivePatchJson<PublishQueuePolicy>("publish-queue/policy", {
          auto_approve_enabled: enabled,
        });
        setPolicy(updated);
        await load();
        toast.success(
          enabled
            ? "Auto approve enabled — simulate-only packs approve without manual confirm."
            : "Manual mode — each publish pack waits for your approval.",
        );
      } catch (exc) {
        toast.error(exc instanceof HiveApiError ? exc.message : "Policy update failed.");
      } finally {
        setPolicyBusy(false);
      }
    },
    [load],
  );

  const reviewOne = useCallback(
    async (id: string, decision: "approve" | "reject") => {
      setBusyId(id);
      onError(null);
      try {
        await hivePostJson(`publish-queue/${encodeURIComponent(id)}/review`, { decision });
        toast.success(decision === "approve" ? "Publish pack approved (simulate)." : "Publish pack rejected.");
        if (decision !== "approve" || detailItem?.id !== id) {
          setDetailItem((prev) => (prev?.id === id ? null : prev));
        }
        await load();
      } catch (exc) {
        onError(exc instanceof HiveApiError ? exc.message : "Review failed.");
      } finally {
        setBusyId(null);
      }
    },
    [detailItem?.id, load, onError],
  );

  const bulkReviewPending = useCallback(
    async (decision: "approve" | "reject", ids: string[]) => {
      if (!ids.length) return;
      setBulkBusy(true);
      onError(null);
      try {
        const out = await hivePostJson<{ updated: number }>("publish-queue/bulk-review", {
          deliverable_ids: ids,
          decision,
        });
        toast.success(`${out.updated} pack(s) ${decision === "approve" ? "approved" : "cleared"}.`);
        setDetailItem(null);
        await load();
      } catch (exc) {
        onError(exc instanceof HiveApiError ? exc.message : "Bulk review failed.");
      } finally {
        setBulkBusy(false);
      }
    },
    [load, onError],
  );

  const approveAllVisible = useCallback(async () => {
    const ids = filteredRows.filter((row) => row.status === "pending").map((row) => row.id);
    if (!ids.length) return;
    const ok = window.confirm(`Approve ${ids.length} pending publish pack${ids.length === 1 ? "" : "s"}?`);
    if (!ok) return;
    await bulkReviewPending("approve", ids);
  }, [bulkReviewPending, filteredRows]);

  const clearAllVisible = useCallback(async () => {
    const ids = filteredRows.filter((row) => row.status === "pending").map((row) => row.id);
    if (!ids.length) return;
    const ok = window.confirm(`Clear ${ids.length} pending publish pack${ids.length === 1 ? "" : "s"} (reject)?`);
    if (!ok) return;
    setClearAllBusy(true);
    try {
      await bulkReviewPending("reject", ids);
    } finally {
      setClearAllBusy(false);
    }
  }, [bulkReviewPending, filteredRows]);

  if (loading && !snapshot) {
    return <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />;
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <>
      <div id="publish-queue" className="v4-marketplace-shell shrink-0 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-(--qs-text)">Publish Queue</p>
            <p className="mt-1 text-xs text-(--qs-text-3)">
              Verified publish packs — simulate-only approval. Live Instagram is Phase C.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 font-mono text-[10px]">
            <span className="rounded-full bg-pollen/15 px-2 py-1 text-pollen">{snapshot.pending_count} pending</span>
            <span className="rounded-full bg-(--qs-green)/15 px-2 py-1 text-(--qs-green)">
              {snapshot.approved_count} approved
            </span>
            <span className="rounded-full bg-(--qs-red)/15 px-2 py-1 text-(--qs-red)">
              {snapshot.rejected_count} rejected
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-3 md:flex-row md:items-stretch">
          <input
            className="qs-input min-w-0 flex-1"
            placeholder="Filter publish packs by title / channel / status…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <label
            className="flex shrink-0 items-center justify-between gap-2 rounded-lg border border-pollen/35 bg-black/25 px-3 py-2 text-xs text-(--qs-text-2) md:min-w-[11.5rem]"
            title="Auto approve commits simulate-only publish packs without manual confirm."
          >
            <span className="whitespace-nowrap font-medium lowercase">
              {policy.auto_approve_enabled ? "auto approve" : "manual"}
            </span>
            <HiveSwitch
              checked={Boolean(policy.auto_approve_enabled)}
              disabled={policyBusy || bulkBusy}
              aria-label="Toggle auto approve for publish queue"
              onCheckedChange={(checked) => void patchAutoApprove(checked)}
            />
          </label>
          <QsSelect
            className="w-full min-w-0 md:w-40 md:shrink-0"
            value={statusFilter}
            onValueChange={(next) => setStatusFilter(next as StatusFilter)}
            options={[
              { value: "all", label: "all statuses" },
              { value: "pending", label: "pending" },
              { value: "approved", label: "approved" },
              { value: "rejected", label: "rejected" },
            ]}
          />
        </div>

        {policy.auto_approve_enabled ? (
          <p className="text-xs text-pollen">
            Auto approve is ON — eligible simulate-only packs leave the queue automatically. Live channel posts stay
            manual.
          </p>
        ) : null}

        <div>
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--qs-text-3)">
              Publish packs
              {filteredRows.length > 0 ? (
                <span className="ml-2 font-normal normal-case tracking-normal text-(--qs-text-4)">
                  ({filteredRows.length})
                </span>
              ) : null}
            </p>
            <div className="flex flex-wrap items-center gap-2">
              {pendingRows.length > 0 ? <V4Badge tone="gold">{pendingRows.length} pending</V4Badge> : null}
            </div>
          </div>

          <div className="v4-sessions-list-scroll hive-scrollbar">
            {filteredRows.length === 0 ? (
              <div className="rounded-xl border border-dashed border-pollen/35 bg-black/20 px-4 py-6 text-center">
                <p className="text-sm text-(--qs-text-2)">
                  {snapshot.items.length === 0
                    ? policy.auto_approve_enabled
                      ? "No publish packs — auto approve cleared the queue."
                      : "No publish packs yet. Run Marketing Ops / Publish Pack Bee — verified packs appear here."
                    : "No publish packs match this filter."}
                </p>
                {snapshot.items.length > 0 ? (
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm mt-3"
                    onClick={() => {
                      setQuery("");
                      setStatusFilter("all");
                    }}
                  >
                    Reset filters
                  </button>
                ) : null}
              </div>
            ) : (
              visibleRows.map((item) => {
                const hookCount = item.hook_variants?.length ?? 0;
                const hasMedia = Boolean(item.media_url?.trim());
                const routeTags = [
                  item.channel,
                  item.status,
                  policy.auto_approve_enabled ? "auto-approve" : "manual-approve",
                  "simulate-only",
                ];
                const packTags = item.tags.slice(0, 6);
                const progressPct = packProgressPct(item.status);

                return (
                  <div key={item.id} className="v4-session-row v4-session-row--pollen">
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex flex-wrap items-center gap-2">
                        <span className="font-(family-name:--font-jetbrains-mono) text-[11px] text-(--qs-text-3)">
                          {shortPackId(item.id)}
                        </span>
                        <V4Badge tone={statusTone(item.status)}>{item.status}</V4Badge>
                        <V4Badge tone="purple">{item.channel}</V4Badge>
                      </div>
                      <p className="v4-session-goal text-sm font-medium text-(--qs-text)" title={item.title}>
                        {item.title}
                      </p>
                      <p className="mt-1 line-clamp-2 text-xs text-(--qs-text-3)">{item.body_preview}</p>

                      <div className="mt-2 space-y-1.5">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-3)">
                            Pack preview
                          </p>
                          <V4Badge tone="gold">heuristic-v1</V4Badge>
                        </div>
                        <p className="text-xs text-(--qs-text-3)">
                          {item.cta ? `${item.cta} · ` : ""}
                          {item.hashtags.length
                            ? item.hashtags.map((tag) => `#${tag}`).join(" ")
                            : "No hashtags"}
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {routeTags.map((tag) => (
                            <V4Badge key={`${item.id}-route-${tag}`} tone="info">
                              {tag}
                            </V4Badge>
                          ))}
                          {hookCount > 0 ? <V4Badge tone="gold">{hookCount} hooks</V4Badge> : null}
                          {hasMedia ? <V4Badge tone="ok">media</V4Badge> : <V4Badge tone="warn">no media</V4Badge>}
                          <PublishMediaMissingBadge channel={item.channel} mediaUrl={item.media_url} />
                        </div>
                        {packTags.length > 0 ? (
                          <div className="space-y-1">
                            <p className="text-[10px] font-medium uppercase tracking-wider text-(--qs-text-4)">
                              Pack tags
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {packTags.map((slug) => (
                                <PackSkillBadge key={`${item.id}-${slug}`} slug={slug} />
                              ))}
                            </div>
                          </div>
                        ) : null}
                        <ForagerProgressCell
                          pct={progressPct}
                          detail={`Review ${progressPct}% · ${item.status} · simulate-only`}
                        />
                      </div>
                    </div>

                    <div className="flex shrink-0 flex-wrap items-center gap-2">
                      <span className="text-xs text-(--qs-text-3)">
                        {formatTimeAgoIso(item.created_at) ?? "just now"}
                      </span>
                      {item.supervisor_session_id ? (
                        <Link
                          href={`/agents?session=${encodeURIComponent(item.supervisor_session_id)}`}
                          className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                        >
                          <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                          Session
                        </Link>
                      ) : null}
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                        onClick={() => setDetailItem(item)}
                      >
                        <FileText className="h-3.5 w-3.5" aria-hidden />
                        Details
                      </button>
                      {item.status === "pending" ? (
                        <>
                          <Link
                            href={`/knowledge/outputs?highlight=${encodeURIComponent(item.id)}`}
                            className="qs-btn qs-btn--ghost qs-btn--sm"
                          >
                            Edit
                          </Link>
                          <button
                            type="button"
                            className="qs-btn qs-btn--ghost qs-btn--sm"
                            disabled={busyId === item.id || bulkBusy || policy.auto_approve_enabled}
                            title={
                              policy.auto_approve_enabled ? "Auto approve is handling the queue." : undefined
                            }
                            onClick={() => void reviewOne(item.id, "reject")}
                          >
                            Reject
                          </button>
                          <button
                            type="button"
                            className={cn("qs-btn qs-btn--primary qs-btn--sm")}
                            disabled={busyId === item.id || bulkBusy || policy.auto_approve_enabled}
                            title={
                              policy.auto_approve_enabled ? "Auto approve is handling the queue." : undefined
                            }
                            onClick={() => void reviewOne(item.id, "approve")}
                          >
                            {busyId === item.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                            ) : null}
                            Approve
                          </button>
                        </>
                      ) : null}
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
          {showAllRows && filteredRows.length > PACK_PREVIEW_LIMIT ? (
            <button
              type="button"
              className="qs-btn qs-btn--ghost mt-3 w-full justify-center py-2.5 text-sm font-semibold"
              onClick={() => setShowAllRows(false)}
            >
              Show less
            </button>
          ) : null}

          {filteredRows.some((row) => row.status === "pending") && !policy.auto_approve_enabled ? (
            <button
              type="button"
              className="qs-btn qs-btn--primary mt-3 w-full justify-center py-2.5 text-sm font-semibold disabled:opacity-45"
              disabled={busyId !== null || bulkBusy}
              onClick={() => void approveAllVisible()}
            >
              {bulkBusy ? "Approving…" : `Approve all (${filteredRows.filter((row) => row.status === "pending").length})`}
            </button>
          ) : null}

          {filteredRows.some((row) => row.status === "pending") ? (
            <button
              type="button"
              className="qs-btn qs-btn--danger mt-3 w-full justify-center py-2.5 text-sm font-semibold disabled:opacity-45"
              disabled={clearAllBusy || busyId !== null || bulkBusy}
              onClick={() => void clearAllVisible()}
            >
              {clearAllBusy
                ? "Clearing…"
                : query.trim() || statusFilter !== "all"
                  ? `Clear filtered (${filteredRows.filter((row) => row.status === "pending").length})`
                  : `Clear all (${filteredRows.filter((row) => row.status === "pending").length})`}
            </button>
          ) : null}
        </div>
      </div>

      <PublishPackDetailModal
        item={detailItem}
        busy={detailItem ? busyId === detailItem.id : false}
        onClose={() => setDetailItem(null)}
        onApprove={(id) => void reviewOne(id, "approve")}
        onReject={(id) => void reviewOne(id, "reject")}
      />
    </>
  );
}

export const ExecutionStudioPublishQueuePanel = memo(ExecutionStudioPublishQueuePanelInner);
