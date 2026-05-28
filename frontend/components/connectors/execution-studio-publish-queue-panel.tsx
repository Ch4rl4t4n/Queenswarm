"use client";

import { ExternalLink, FileText, Loader2 } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { PublishPackDetailModal } from "@/components/connectors/publish-pack-detail-modal";
import { PublishMediaMissingBadge } from "@/components/connectors/publish-media-preview";
import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { PublishQueueItem, PublishQueueSnapshot } from "@/lib/publish-queue-types";
import { cn } from "@/lib/utils";

export type { PublishQueueItem, PublishQueueSnapshot } from "@/lib/publish-queue-types";

export interface ExecutionStudioPublishQueuePanelProps {
  onError: (message: string | null) => void;
}

function statusTone(status: PublishQueueItem["status"]): "ok" | "warn" | "err" | "info" {
  if (status === "approved") return "ok";
  if (status === "rejected") return "err";
  return "warn";
}

function PublishPackCard({
  item,
  selected,
  busy,
  onToggleSelected,
  onReview,
  onOpenDetails,
}: {
  item: PublishQueueItem;
  selected: boolean;
  busy: boolean;
  onToggleSelected: (id: string, checked: boolean) => void;
  onReview: (id: string, decision: "approve" | "reject") => void;
  onOpenDetails: (item: PublishQueueItem) => void;
}): JSX.Element {
  const hookCount = item.hook_variants?.length ?? 0;
  const hasMedia = Boolean(item.media_url?.trim());

  return (
    <article className="v4-dream-cycle-card flex h-full flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex items-start gap-2">
            {item.status === "pending" ? (
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 shrink-0 accent-pollen"
                checked={selected}
                onChange={(event) => onToggleSelected(item.id, event.currentTarget.checked)}
                aria-label={`Select ${item.title}`}
              />
            ) : null}
            <p className="line-clamp-2 text-sm font-semibold text-(--qs-text)">{item.title}</p>
          </div>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">{item.channel}</p>
        </div>
        <V4Badge tone={statusTone(item.status)}>{item.status}</V4Badge>
      </div>

      <p className="line-clamp-2 text-xs leading-relaxed text-(--qs-text-3)">{item.body_preview}</p>

      <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-3 py-2">
        <p className="v4-field-label text-[10px] text-cyan-300/90">Pack preview</p>
        <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-(--qs-text-2)">
          {item.cta ? `${item.cta} · ` : ""}
          {item.hashtags.length ? item.hashtags.map((tag) => `#${tag}`).join(" ") : "No hashtags"}
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {item.tags.slice(0, 2).map((tag) => (
          <V4Badge key={tag} tone="info">
            {tag}
          </V4Badge>
        ))}
        {hookCount > 0 ? <V4Badge tone="gold">{hookCount} hooks</V4Badge> : null}
        {hasMedia ? <V4Badge tone="ok">media</V4Badge> : <V4Badge tone="warn">no media</V4Badge>}
        <PublishMediaMissingBadge channel={item.channel} mediaUrl={item.media_url} />
      </div>

      <div className="v4-dream-cycle-card-actions">
        {item.supervisor_session_id ? (
          <Link
            href={`/agents?session=${encodeURIComponent(item.supervisor_session_id)}`}
            className="inline-flex items-center gap-1 text-xs text-pollen hover:underline"
          >
            <ExternalLink className="h-3.5 w-3.5" aria-hidden />
            Open session
          </Link>
        ) : null}
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
          onClick={() => onOpenDetails(item)}
        >
          <FileText className="h-3.5 w-3.5" aria-hidden />
          View details
        </button>
        {item.status === "pending" ? (
          <>
            <Link
              href={`/knowledge/outputs?highlight=${encodeURIComponent(item.id)}`}
              className={cn("qs-btn qs-btn--ghost qs-btn--sm")}
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
      </div>
    </article>
  );
}

function ExecutionStudioPublishQueuePanelInner({ onError }: ExecutionStudioPublishQueuePanelProps) {
  const [snapshot, setSnapshot] = useState<PublishQueueSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [detailItem, setDetailItem] = useState<PublishQueueItem | null>(null);

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
      <div id="publish-queue" className="qs-bubble qs-bubble--tint-amber shrink-0 space-y-3 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-(--qs-text)">Publish Queue</p>
            <p className="mt-1 text-xs text-(--qs-text-3)">
              Verified publish packs — simulate-only approval. Live Instagram is Phase C.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 font-mono text-[10px] text-(--qs-text-3)">
            <span className="text-pollen">{snapshot.pending_count} pending</span>
            <span className="text-(--qs-green)">{snapshot.approved_count} approved</span>
            <span className="text-(--qs-red)">{snapshot.rejected_count} rejected</span>
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

        {snapshot.items.length === 0 ? (
          <p className="text-xs text-(--qs-text-3)">
            No publish packs yet. Run Marketing Ops / Publish Pack Bee — verified packs appear here automatically.
          </p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {snapshot.items.map((item) => (
              <PublishPackCard
                key={item.id}
                item={item}
                selected={selected.has(item.id)}
                busy={busyId === item.id}
                onToggleSelected={toggleSelected}
                onReview={(id, decision) => void reviewOne(id, decision)}
                onOpenDetails={setDetailItem}
              />
            ))}
          </div>
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
