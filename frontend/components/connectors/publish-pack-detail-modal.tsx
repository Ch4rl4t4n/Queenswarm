"use client";

import { ExternalLink, X } from "lucide-react";
import Link from "next/link";

import { PublishMediaMissingBadge, PublishMediaPreview } from "@/components/connectors/publish-media-preview";
import { HiveModalShell } from "@/components/hive/hive-modal-shell";
import type { PublishQueueItem } from "@/lib/publish-queue-types";
import { V4Badge } from "@/components/ui/v4";
import { cn } from "@/lib/utils";

function statusTone(status: PublishQueueItem["status"]): "ok" | "warn" | "err" | "info" {
  if (status === "approved") return "ok";
  if (status === "rejected") return "err";
  return "warn";
}

export interface PublishPackDetailModalProps {
  item: PublishQueueItem | null;
  busy: boolean;
  onClose: () => void;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
}

/** Full publish pack inspect overlay — hook variants, body, media, session link. */
export function PublishPackDetailModal({
  item,
  busy,
  onClose,
  onApprove,
  onReject,
}: PublishPackDetailModalProps): JSX.Element | null {
  if (!item) {
    return null;
  }

  const showActions = item.status === "pending" && onApprove && onReject;

  return (
    <HiveModalShell
      open
      onClose={onClose}
      labelledBy="publish-pack-detail-title"
      backdropClassName="bg-black/70 backdrop-blur-sm"
      panelClassName="v4-card flex max-h-[90vh] w-full max-w-2xl flex-col gap-4 overflow-hidden"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <span className="v4-label-kicker">Publish pack</span>
          <h3 id="publish-pack-detail-title" className="text-lg font-semibold text-(--qs-text)">
            {item.title}
          </h3>
          <div className="flex flex-wrap items-center gap-2">
            <V4Badge tone={statusTone(item.status)}>{item.status}</V4Badge>
            <span className="font-mono text-[10px] uppercase text-cyan">{item.channel}</span>
            {item.tags.map((tag) => (
              <V4Badge key={tag} tone="info">
                {tag}
              </V4Badge>
            ))}
          </div>
        </div>
        <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm shrink-0" onClick={onClose} aria-label="Close">
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>

      <div className="hive-scrollbar min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        <section>
          <p className="v4-field-label text-[10px] text-cyan-300/90">Caption</p>
          <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-(--qs-text-2)">
            {item.body || item.body_preview}
          </p>
        </section>

        {item.cta ? (
          <section>
            <p className="v4-field-label text-[10px] text-cyan-300/90">CTA</p>
            <p className="mt-1 text-sm text-(--qs-text-2)">{item.cta}</p>
          </section>
        ) : null}

        {item.hashtags.length > 0 ? (
          <section>
            <p className="v4-field-label text-[10px] text-cyan-300/90">Hashtags</p>
            <p className="mt-1 font-mono text-xs text-(--qs-text-3)">
              {item.hashtags.map((tag) => `#${tag}`).join(" ")}
            </p>
          </section>
        ) : null}

        {item.hook_variants && item.hook_variants.length > 0 ? (
          <section>
            <p className="v4-field-label text-[10px] text-pollen">Hook variants</p>
            <ul className="mt-2 space-y-2">
              {item.hook_variants.map((hook) => (
                <li
                  key={hook.id}
                  className="rounded-lg border border-(--qs-border)/60 bg-black/20 px-3 py-2 text-xs text-(--qs-text-2)"
                >
                  <span className="font-mono text-[10px] uppercase text-cyan">{hook.style}</span>
                  <p className="mt-1">{hook.hook}</p>
                  {hook.rationale ? (
                    <p className="mt-1 text-[11px] text-(--qs-text-3)">{hook.rationale}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <section>
          <p className="v4-field-label text-[10px] text-cyan-300/90">Media</p>
          <div className="mt-2 max-w-lg">
            <PublishMediaPreview url={item.media_url} channel={item.channel} title={item.title} />
            <PublishMediaMissingBadge channel={item.channel} mediaUrl={item.media_url} />
          </div>
        </section>

        {item.supervisor_session_id ? (
          <Link
            href={`/agents?session=${encodeURIComponent(item.supervisor_session_id)}`}
            className="inline-flex items-center gap-1 text-xs text-cyan hover:text-pollen"
          >
            Open supervisor session <ExternalLink className="h-3.5 w-3.5" aria-hidden />
          </Link>
        ) : null}

        <p className="font-mono text-[10px] text-(--qs-text-4)">
          Created {new Date(item.created_at).toLocaleString()} · {item.id}
        </p>
      </div>

      {showActions ? (
        <div className="flex flex-wrap justify-end gap-2 border-t border-(--qs-border)/60 pt-3">
          <Link
            href={`/knowledge/outputs?highlight=${encodeURIComponent(item.id)}`}
            className={cn("qs-btn qs-btn--ghost qs-btn--sm")}
          >
            Edit in Outputs
          </Link>
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm"
            disabled={busy}
            onClick={() => onReject(item.id)}
          >
            Reject
          </button>
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm"
            disabled={busy}
            onClick={() => onApprove(item.id)}
          >
            Approve
          </button>
        </div>
      ) : null}
    </HiveModalShell>
  );
}
