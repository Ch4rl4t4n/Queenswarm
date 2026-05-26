"use client";

import { ExternalLink, ImageOff } from "lucide-react";
import { memo, useCallback, useState } from "react";

import {
  classifyPublishMediaUrl,
  isSafePublishMediaUrl,
  resolvePublishMediaPreviewMode,
  type PublishMediaKind,
} from "@/lib/publish-media";
import { cn } from "@/lib/utils";

export interface PublishMediaPreviewProps {
  url: string | null | undefined;
  channel?: string | null;
  title?: string;
  compact?: boolean;
  className?: string;
}

function PublishMediaPreviewInner({
  url,
  channel,
  title = "Publish media",
  compact = false,
  className,
}: PublishMediaPreviewProps) {
  const [loadFailed, setLoadFailed] = useState(false);
  const safe = isSafePublishMediaUrl(url);
  const mode = resolvePublishMediaPreviewMode(url, channel);
  const kind: PublishMediaKind | null = safe ? classifyPublishMediaUrl(url) : null;

  const onMediaError = useCallback(() => {
    setLoadFailed(true);
  }, []);

  if (!url?.trim()) {
    return (
      <p className={cn("text-xs text-(--qs-muted)", className)}>
        No media URL — add image/video in Outputs or generate via Venice.
      </p>
    );
  }

  if (!safe || loadFailed || mode === "link") {
    return (
      <a
        href={url}
        target="_blank"
        rel="noreferrer noopener"
        className={cn(
          "inline-flex items-center gap-1 text-xs text-cyan hover:underline",
          className,
        )}
      >
        {loadFailed ? "Media preview failed — open URL" : "Open media URL"}
        <ExternalLink className="size-3" aria-hidden />
      </a>
    );
  }

  const frameClass = cn(
    "overflow-hidden rounded-lg border border-(--qs-border) bg-black/30",
    compact ? "max-h-40" : "max-h-72",
    className,
  );

  return (
    <figure className={frameClass}>
      {mode === "video" ? (
        <video
          src={url}
          controls
          preload="metadata"
          className="max-h-72 w-full object-contain"
          onError={onMediaError}
          aria-label={title}
        />
      ) : (
        // eslint-disable-next-line @next/next/no-img-element -- external CDN URLs from operator packs
        <img
          src={url}
          alt={title}
          referrerPolicy="no-referrer"
          className="max-h-72 w-full object-contain"
          onError={onMediaError}
        />
      )}
      <figcaption className="flex flex-wrap items-center justify-between gap-2 border-t border-(--qs-border)/60 px-2 py-1.5 text-[10px] text-(--qs-muted)">
        <span className="font-mono uppercase text-cyan">{kind ?? "media"}</span>
        <a
          href={url}
          target="_blank"
          rel="noreferrer noopener"
          className="inline-flex items-center gap-1 hover:text-pollen"
        >
          Open <ExternalLink className="size-3" aria-hidden />
        </a>
      </figcaption>
    </figure>
  );
}

export const PublishMediaPreview = memo(PublishMediaPreviewInner);
PublishMediaPreview.displayName = "PublishMediaPreview";

export function PublishMediaMissingBadge({
  channel,
  mediaUrl,
}: {
  channel?: string | null;
  mediaUrl?: string | null;
}) {
  const ch = String(channel ?? "").toLowerCase();
  if (ch !== "tiktok" || mediaUrl?.trim()) return null;
  return (
    <span className="inline-flex items-center gap-1 text-[10px] text-pollen">
      <ImageOff className="size-3" aria-hidden />
      TikTok needs video URL
    </span>
  );
}
