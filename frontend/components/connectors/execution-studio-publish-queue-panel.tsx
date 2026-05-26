"use client";

import { ExternalLink, Loader2 } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { V4Badge } from "@/components/ui/v4";
import { PublishMediaMissingBadge, PublishMediaPreview } from "@/components/connectors/publish-media-preview";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface PublishQueueItem {
  id: string;
  title: string;
  channel: string;
  body: string;
  body_preview: string;
  hashtags: string[];
  cta: string;
  media_url: string | null;
  media_kind: string | null;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  supervisor_session_id: string | null;
  tags: string[];
  hook_variants?: { id: string; style: string; hook: string; rationale?: string }[];
}

export interface PublishQueueSnapshot {
  enabled: boolean;
  count: number;
  pending_count: number;
  approved_count: number;
  rejected_count: number;
  items: PublishQueueItem[];
}

export interface ExecutionStudioPublishQueuePanelProps {
  onError: (message: string | null) => void;
}

function statusTone(status: PublishQueueItem["status"]): "ok" | "warn" | "err" | "info" {
  if (status === "approved") return "ok";
  if (status === "rejected") return "err";
  return "warn";
}

function ExecutionStudioPublishQueuePanelInner({ onError }: ExecutionStudioPublishQueuePanelProps) {
  const [snapshot, setSnapshot] = useState<PublishQueueSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

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
        await load();
      } catch (exc) {
        onError(exc instanceof HiveApiError ? exc.message : "Review failed.");
      } finally {
        setBusyId(null);
      }
    },
    [load, onError],
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
        <div className="flex flex-wrap gap-2">
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
        <ul className="space-y-2">
          {snapshot.items.map((item) => (
            <li key={item.id} className="qs-bubble-inner space-y-2 p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    {item.status === "pending" ? (
                      <input
                        type="checkbox"
                        className="h-4 w-4 accent-pollen"
                        checked={selected.has(item.id)}
                        onChange={(event) => toggleSelected(item.id, event.currentTarget.checked)}
                        aria-label={`Select ${item.title}`}
                      />
                    ) : null}
                    <p className="text-sm font-semibold text-(--qs-text)">{item.title}</p>
                    <V4Badge tone={statusTone(item.status)}>{item.status}</V4Badge>
                    <span className="font-mono text-[10px] uppercase text-cyan">{item.channel}</span>
                  </div>
                  <p className="mt-1 text-xs text-(--qs-text-2)">{item.body_preview}</p>
                  {item.hashtags.length ? (
                    <p className="mt-1 font-mono text-[10px] text-(--qs-text-4)">
                      {item.hashtags.map((tag) => `#${tag}`).join(" ")}
                    </p>
                  ) : null}
                  {item.hook_variants && item.hook_variants.length > 0 ? (
                    <div className="mt-2 space-y-1">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-pollen">Hook variants</p>
                      <ul className="space-y-1">
                        {item.hook_variants.slice(0, 4).map((hook) => (
                          <li
                            key={hook.id}
                            className="rounded border border-(--qs-border)/60 bg-black/20 px-2 py-1 font-mono text-[10px] text-(--qs-text-2)"
                          >
                            <span className="text-cyan">{hook.style}:</span> {hook.hook}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  <div className="mt-2 max-w-md">
                    <PublishMediaPreview
                      url={item.media_url}
                      channel={item.channel}
                      title={item.title}
                      compact
                    />
                    <PublishMediaMissingBadge channel={item.channel} mediaUrl={item.media_url} />
                  </div>
                  {item.supervisor_session_id ? (
                    <Link
                      href={`/agents?session=${encodeURIComponent(item.supervisor_session_id)}`}
                      className="mt-1 inline-flex items-center gap-1 text-[10px] text-cyan hover:text-pollen"
                    >
                      Open session <ExternalLink className="h-3 w-3" aria-hidden />
                    </Link>
                  ) : null}
                </div>
                {item.status === "pending" ? (
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="qs-btn qs-btn--primary qs-btn--sm"
                      disabled={busyId === item.id}
                      onClick={() => void reviewOne(item.id, "approve")}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm"
                      disabled={busyId === item.id}
                      onClick={() => void reviewOne(item.id, "reject")}
                    >
                      Reject
                    </button>
                    <Link
                      href={`/knowledge/outputs?highlight=${encodeURIComponent(item.id)}`}
                      className={cn("qs-btn qs-btn--ghost qs-btn--sm")}
                    >
                      Edit in Outputs
                    </Link>
                  </div>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export const ExecutionStudioPublishQueuePanel = memo(ExecutionStudioPublishQueuePanelInner);
