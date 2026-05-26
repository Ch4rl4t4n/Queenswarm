"use client";

import { Check, ChevronLeft, ChevronRight, Layers, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { V4Badge } from "@/components/ui/v4";
import { cn } from "@/lib/utils";

export interface ApprovalDeckItem {
  id: string;
  title: string;
  description: string;
  meta?: string;
  badge?: string;
  badgeTone?: "gold" | "purple" | "info" | "warn" | "ok" | "err";
}

export interface ApprovalCardDeckProps {
  items: ApprovalDeckItem[];
  busyId: string | null;
  bulkBusy?: boolean;
  emptyLabel?: string;
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string) => Promise<void>;
  onApproveAll?: () => Promise<void>;
  onRejectAll?: () => Promise<void>;
  className?: string;
}

/** Stacked playing-card deck — one card in focus, auto-advance after action. */
export function ApprovalCardDeck({
  items,
  busyId,
  bulkBusy = false,
  emptyLabel = "Nothing pending.",
  onApprove,
  onReject,
  onApproveAll,
  onRejectAll,
  className,
}: ApprovalCardDeckProps) {
  const [index, setIndex] = useState(0);

  const safeIndex = items.length ? Math.min(index, items.length - 1) : 0;
  const current = items[safeIndex];
  const behind = items.slice(safeIndex + 1, safeIndex + 3);

  useEffect(() => {
    setIndex((i) => Math.min(i, Math.max(0, items.length - 1)));
  }, [items]);

  const goPrev = useCallback(() => {
    setIndex((i) => Math.max(0, i - 1));
  }, []);

  const goNext = useCallback(() => {
    setIndex((i) => Math.min(items.length - 1, i + 1));
  }, [items.length]);

  const wrapAction = useCallback(async (id: string, action: (itemId: string) => Promise<void>) => {
    await action(id);
  }, []);

  const deckLabel = useMemo(() => {
    if (!items.length) return "0 / 0";
    return `${safeIndex + 1} / ${items.length}`;
  }, [items.length, safeIndex]);

  if (!items.length) {
    return <p className="text-sm text-(--qs-text-3)">{emptyLabel}</p>;
  }

  return (
    <div className={cn("approval-card-deck", className)}>
      <div className="approval-card-deck__toolbar">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-pollen" aria-hidden />
          <span className="font-mono text-xs text-(--qs-text-3)">{deckLabel}</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {onApproveAll ? (
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              disabled={bulkBusy || busyId !== null}
              onClick={() => void onApproveAll()}
            >
              {bulkBusy ? "Processing…" : "Approve all"}
            </button>
          ) : null}
          {onRejectAll ? (
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              disabled={bulkBusy || busyId !== null}
              onClick={() => void onRejectAll()}
            >
              Reject all
            </button>
          ) : null}
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm !px-2"
            disabled={safeIndex <= 0}
            aria-label="Previous card"
            onClick={goPrev}
          >
            <ChevronLeft className="h-4 w-4" aria-hidden />
          </button>
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm !px-2"
            disabled={safeIndex >= items.length - 1}
            aria-label="Next card"
            onClick={goNext}
          >
            <ChevronRight className="h-4 w-4" aria-hidden />
          </button>
        </div>
      </div>

      <div className="approval-card-deck__stage">
        {behind
          .slice()
          .reverse()
          .map((row, revIdx) => {
            const depth = behind.length - revIdx;
            return (
              <div
                key={row.id}
                className="approval-card-deck__card approval-card-deck__card--back"
                style={{
                  transform: `translateY(${depth * 10}px) scale(${1 - depth * 0.03})`,
                  zIndex: 10 - depth,
                }}
                aria-hidden
              >
                <p className="truncate text-sm font-medium text-(--qs-text-2)">{row.title}</p>
              </div>
            );
          })}

        {current ? (
          <article
            className="approval-card-deck__card approval-card-deck__card--front"
            style={{ zIndex: 20 }}
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <p className="text-base font-semibold leading-snug text-(--qs-text)">{current.title}</p>
              {current.badge ? (
                <V4Badge tone={current.badgeTone ?? "info"}>{current.badge}</V4Badge>
              ) : null}
            </div>
            <p className="mt-3 flex-1 overflow-y-auto text-sm leading-relaxed text-(--qs-text-2)">
              {current.description}
            </p>
            {current.meta ? (
              <p className="mt-3 font-mono text-[11px] text-(--qs-text-3)">{current.meta}</p>
            ) : null}
            <div className="mt-4 flex flex-wrap gap-2 border-t border-(--qs-border) pt-4">
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm min-w-[5.5rem]"
                disabled={busyId === current.id || bulkBusy}
                onClick={() => void wrapAction(current.id, onReject)}
              >
                <X className="h-3.5 w-3.5" aria-hidden />
                Reject
              </button>
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm min-w-[5.5rem]"
                disabled={busyId === current.id || bulkBusy}
                onClick={() => void wrapAction(current.id, onApprove)}
              >
                <Check className="h-3.5 w-3.5" aria-hidden />
                Approve
              </button>
            </div>
          </article>
        ) : null}
      </div>
    </div>
  );
}
