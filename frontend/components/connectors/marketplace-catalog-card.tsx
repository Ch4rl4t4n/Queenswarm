"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface MarketplaceCatalogCardProps {
  title: ReactNode;
  indexLabel?: string;
  kicker?: string;
  statusBadge: ReactNode;
  summary: ReactNode;
  manifestLabel: string;
  manifestBody: ReactNode;
  metaLine?: ReactNode;
  badges?: ReactNode;
  docLink?: ReactNode;
  footMeta?: ReactNode;
  actions: ReactNode;
  className?: string;
}

/** Shared marketplace / publish-queue catalog card (screenshot-aligned hub-catalog layout). */
export function MarketplaceCatalogCard({
  title,
  indexLabel,
  kicker,
  statusBadge,
  summary,
  manifestLabel,
  manifestBody,
  metaLine,
  badges,
  docLink,
  footMeta,
  actions,
  className,
}: MarketplaceCatalogCardProps): JSX.Element {
  return (
    <article className={cn("hub-catalog-card", className)}>
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <div className="hub-catalog-card__title">{title}</div>
          {indexLabel ? (
            <p className="font-mono text-[10px] tracking-wide text-(--qs-text-3)">{indexLabel}</p>
          ) : null}
          {kicker ? (
            <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">{kicker}</p>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">{statusBadge}</div>
      </header>

      <p className="hub-catalog-card__summary">{summary}</p>

      <div className="hub-catalog-card__manifest">
        <p className="hub-catalog-card__manifest-label">{manifestLabel}</p>
        <div className="hub-catalog-card__manifest-meta">{manifestBody}</div>
      </div>

      {metaLine ? <p className="font-mono text-[11px] text-(--qs-text-3)">{metaLine}</p> : null}

      {badges ? <div className="hub-catalog-card__status-row">{badges}</div> : null}

      {docLink}

      <footer className="hub-catalog-card__foot">
        {footMeta ? <span className="font-mono text-[11px] text-(--qs-text-3)">{footMeta}</span> : <span />}
        <div className="hub-catalog-card__actions">{actions}</div>
      </footer>
    </article>
  );
}
