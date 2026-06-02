"use client";

import { ExternalLink, FileText, Loader2 } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { MarketplaceCatalogCard } from "@/components/connectors/marketplace-catalog-card";
import { PublishPackDetailModal } from "@/components/connectors/publish-pack-detail-modal";
import { PublishMediaMissingBadge } from "@/components/connectors/publish-media-preview";
import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { PublishQueueItem, PublishQueueSnapshot } from "@/lib/publish-queue-types";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";
import { cn } from "@/lib/utils";

export type { PublishQueueItem, PublishQueueSnapshot } from "@/lib/publish-queue-types";

export interface ExecutionStudioPublishQueuePanelProps {
  onError: (message: string | null) => void;
}

type ChannelFilter = "all" | "pending" | "approved" | "rejected";

const CHANNEL_FILTERS: { id: ChannelFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "pending", label: "Pending" },
  { id: "approved", label: "Approved" },
  { id: "rejected", label: "Rejected" },
];

function statusTone(status: PublishQueueItem["status"]): "ok" | "warn" | "err" | "info" {
  if (status === "approved") return "ok";
  if (status === "rejected") return "err";
  return "warn";
}

function PublishPackCard({
  item,
  index,
  selected,
  busy,
  onToggleSelected,
  onReview,
  onOpenDetails,
}: {
  item: PublishQueueItem;
  index: number;
  selected: boolean;
  busy: boolean;
  onToggleSelected: (id: string, checked: boolean) => void;
  onReview: (id: string, decision: "approve" | "reject") => void;
  onOpenDetails: (item: PublishQueueItem) => void;
}): JSX.Element {
  const hookCount = item.hook_variants?.length ?? 0;
  const hasMedia = Boolean(item.media_url?.trim());

  return (
    <MarketplaceCatalogCard
      title={
        <span className="inline-flex items-start gap-2">
          {item.status === "pending" ? (
            <input
              type="checkbox"
              className="mt-0.5 h-4 w-4 shrink-0 accent-pollen"
              checked={selected}
              onChange={(event) => onToggleSelected(item.id, event.currentTarget.checked)}
              aria-label={`Select ${item.title}`}
            />
          ) : null}
          <span className="line-clamp-2">{item.title}</span>
        </span>
      }
      indexLabel={`#${index + 1}`}
      kicker={item.channel}
      statusBadge={<V4Badge tone={statusTone(item.status)}>{item.status}</V4Badge>}
      summary={item.body_preview}
      manifestLabel="Pack preview"
      manifestBody={
        <>
          {item.cta ? `${item.cta} · ` : ""}
          {item.hashtags.length ? item.hashtags.map((tag) => `#${tag}`).join(" ") : "No hashtags"}
        </>
      }
      metaLine={item.tags.slice(0, 2).join(" · ") || "publish-pack"}
      badges={
        <>
          {item.tags.slice(0, 2).map((tag) => (
            <V4Badge key={tag} tone="info">
              {tag}
            </V4Badge>
          ))}
          {hookCount > 0 ? <V4Badge tone="gold">{hookCount} hooks</V4Badge> : null}
          {hasMedia ? <V4Badge tone="ok">media</V4Badge> : <V4Badge tone="warn">no media</V4Badge>}
          <PublishMediaMissingBadge channel={item.channel} mediaUrl={item.media_url} />
        </>
      }
      footMeta={item.supervisor_session_id ? "linked session" : undefined}
      actions={
        <>
          {item.supervisor_session_id ? (
            <Link
              href={`/agents?session=${encodeURIComponent(item.supervisor_session_id)}`}
              className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1"
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden />
              Session
            </Link>
          ) : null}
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5" onClick={() => onOpenDetails(item)}>
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
                disabled={busy}
                onClick={() => onReview(item.id, "reject")}
              >
                Reject
              </button>
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm"
                disabled={busy}
                onClick={() => onReview(item.id, "approve")}
              >
                Approve
              </button>
            </>
          ) : null}
        </>
      }
    />
  );
}

function ExecutionStudioPublishQueuePanelInner({ onError }: ExecutionStudioPublishQueuePanelProps) {
  const [snapshot, setSnapshot] = useState<PublishQueueSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [detailItem, setDetailItem] = useState<PublishQueueItem | null>(null);
  const [activeFilter, setActiveFilter] = useState<ChannelFilter>("all");

  const load = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      const data = await hiveGet<PublishQueueSnapshot>("publish-queue");
      setSnapshot(data);
      setSelected((prev) => {
        const pendingIds = new Set(data.items.filter((row) => row.status === "pending").map((row) => row.id));
        return new Set([...prev].filter((id) => pendingIds.has(id)));
      });
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

  const pendingItems = useMemo(
    () => snapshot?.items.filter((row) => row.status === "pending") ?? [],
    [snapshot?.items],
  );

  const visibleItems = useMemo(() => {
    const items = snapshot?.items ?? [];
    if (activeFilter === "all") return items;
    return items.filter((row) => row.status === activeFilter);
  }, [activeFilter, snapshot?.items]);

  const filterCounts = useMemo(() => {
    const items = snapshot?.items ?? [];
    return {
      all: items.length,
      pending: items.filter((row) => row.status === "pending").length,
      approved: items.filter((row) => row.status === "approved").length,
      rejected: items.filter((row) => row.status === "rejected").length,
    };
  }, [snapshot?.items]);

  const pageSize = useGridTwoRowPageSize({ columns: 2 });
  const pagination = usePaginatedSlice(visibleItems, pageSize, `${activeFilter}|${pageSize}`);

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

  const bulkReview = useCallback(
    async (decision: "approve" | "reject") => {
      const ids = [...selected];
      if (!ids.length) return;
      setBulkBusy(true);
      onError(null);
      try {
        const out = await hivePostJson<{ updated: number }>("publish-queue/bulk-review", {
          deliverable_ids: ids,
          decision,
        });
        toast.success(`${out.updated} pack(s) ${decision === "approve" ? "approved" : "rejected"}.`);
        setSelected(new Set());
        setDetailItem(null);
        await load();
      } catch (exc) {
        onError(exc instanceof HiveApiError ? exc.message : "Bulk review failed.");
      } finally {
        setBulkBusy(false);
      }
    },
    [load, onError, selected],
  );

  const toggleSelected = useCallback((id: string, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }, []);

  if (loading && !snapshot) {
    return <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />;
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <>
      <div id="publish-queue" className="v4-marketplace-shell v4-marketplace-shell--paginated shrink-0 space-y-3">
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

        {pendingItems.length > 0 ? (
          <div className="flex flex-wrap justify-end gap-2">
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              disabled={bulkBusy || selected.size === 0}
              onClick={() => void bulkReview("approve")}
            >
              {bulkBusy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
              Approve selected ({selected.size})
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              disabled={bulkBusy || selected.size === 0}
              onClick={() => void bulkReview("reject")}
            >
              Reject selected
            </button>
          </div>
        ) : null}

        <div className="v4-subtab-row w-full max-w-full shrink-0">
          {CHANNEL_FILTERS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={cn("v4-subtab shrink-0 gap-2", activeFilter === tab.id && "v4-subtab--active")}
              onClick={() => setActiveFilter(tab.id)}
            >
              {tab.label}
              <span className="rounded-full bg-white/10 px-1.5 py-0.5 font-mono text-[10px] text-(--qs-text-3)">
                {filterCounts[tab.id]}
              </span>
            </button>
          ))}
        </div>

        <p className="v4-field-label uppercase tracking-[0.08em]">
          Publish packs ({visibleItems.length})
        </p>

        {visibleItems.length === 0 ? (
          <p className="text-xs text-(--qs-text-3)">
            No publish packs in this filter. Run Marketing Ops / Publish Pack Bee — verified packs appear here
            automatically.
          </p>
        ) : (
          <ViewportBoundedPanel
            className="v4-recipe-catalog-panel"
            footer={
              <ListPaginator
                page={pagination.page}
                totalPages={pagination.totalPages}
                totalItems={pagination.totalItems}
                pageSize={pageSize}
                onPageChange={pagination.setPage}
              />
            }
          >
            <div className="hub-catalog-grid">
              {pagination.slice.map((item, idx) => (
                <PublishPackCard
                  key={item.id}
                  item={item}
                  index={(pagination.page - 1) * pageSize + idx}
                  selected={selected.has(item.id)}
                  busy={busyId === item.id}
                  onToggleSelected={toggleSelected}
                  onReview={(id, decision) => void reviewOne(id, decision)}
                  onOpenDetails={setDetailItem}
                />
              ))}
            </div>
          </ViewportBoundedPanel>
        )}
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
