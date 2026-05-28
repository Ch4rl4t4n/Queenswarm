"use client";

import { ChevronLeft, ChevronRight, Layers } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { V4Badge } from "@/components/ui/v4";
import { cn } from "@/lib/utils";

export interface CollectorTab {
  id: string;
  label: string;
  count: number;
  tone?: "gold" | "purple" | "info" | "warn" | "ok" | "err";
}

export interface CollectorCardItem {
  id: string;
  title: string;
  body: string;
  meta?: string;
  badge?: string;
  badgeTone?: "gold" | "purple" | "info" | "warn" | "ok" | "err";
  footer?: React.ReactNode;
}

export interface DynamicCollectorDeckProps {
  tabs: CollectorTab[];
  itemsByTab: Record<string, CollectorCardItem[]>;
  defaultTabId?: string;
  emptyLabel?: string;
  className?: string;
  onTabChange?: (tabId: string) => void;
}

/** Read-only collector — tab filters + stacked card deck (one card in focus). */
export function DynamicCollectorDeck({
  tabs,
  itemsByTab,
  defaultTabId,
  emptyLabel = "Nothing in this collector.",
  className,
  onTabChange,
}: DynamicCollectorDeckProps) {
  const firstTab = tabs[0]?.id ?? "all";
  const [activeTab, setActiveTab] = useState(defaultTabId ?? firstTab);
  const [index, setIndex] = useState(0);

  const items = useMemo(() => itemsByTab[activeTab] ?? [], [itemsByTab, activeTab]);
  const safeIndex = items.length ? Math.min(index, items.length - 1) : 0;
  const current = items[safeIndex];
  const behind = items.slice(safeIndex + 1, safeIndex + 3);

  useEffect(() => {
    setIndex(0);
  }, [activeTab]);

  useEffect(() => {
    setIndex((i) => Math.min(i, Math.max(0, items.length - 1)));
  }, [items]);

  const switchTab = useCallback(
    (tabId: string) => {
      setActiveTab(tabId);
      onTabChange?.(tabId);
    },
    [onTabChange],
  );

  const deckLabel = items.length ? `${safeIndex + 1} / ${items.length}` : "0 / 0";

  return (
    <div className={cn("dynamic-collector-deck", className)}>
      <div className="dynamic-collector-deck__tabs" role="tablist" aria-label="Collector filters">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            className={cn(
              "dynamic-collector-deck__tab",
              activeTab === tab.id && "dynamic-collector-deck__tab--active",
            )}
            onClick={() => switchTab(tab.id)}
          >
            <span>{tab.label}</span>
            <V4Badge tone={activeTab === tab.id ? tab.tone ?? "info" : "info"}>{tab.count}</V4Badge>
          </button>
        ))}
      </div>

      <div className="dynamic-collector-deck__toolbar">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-cyan" aria-hidden />
          <span className="font-mono text-xs text-(--qs-text-3)">{deckLabel}</span>
        </div>
        <div className="flex gap-1">
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm px-2!"
            disabled={safeIndex <= 0}
            aria-label="Previous"
            onClick={() => setIndex((i) => Math.max(0, i - 1))}
          >
            <ChevronLeft className="h-4 w-4" aria-hidden />
          </button>
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm px-2!"
            disabled={safeIndex >= items.length - 1}
            aria-label="Next"
            onClick={() => setIndex((i) => Math.min(items.length - 1, i + 1))}
          >
            <ChevronRight className="h-4 w-4" aria-hidden />
          </button>
        </div>
      </div>

      {!items.length ? (
        <p className="text-sm text-(--qs-text-3)">{emptyLabel}</p>
      ) : (
        <div className="dynamic-collector-deck__stage">
          {behind
            .slice()
            .reverse()
            .map((row, revIdx) => {
              const depth = behind.length - revIdx;
              return (
                <div
                  key={row.id}
                  className="dynamic-collector-deck__card dynamic-collector-deck__card--back"
                  style={{
                    transform: `translateY(${depth * 10}px) scale(${1 - depth * 0.03})`,
                    zIndex: 10 - depth,
                  }}
                  aria-hidden
                >
                  <p className="truncate text-sm text-(--qs-text-2)">{row.title}</p>
                </div>
              );
            })}

          {current ? (
            <article
              className="dynamic-collector-deck__card dynamic-collector-deck__card--front"
              style={{ zIndex: 20 }}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="text-base font-semibold leading-snug text-(--qs-text)">{current.title}</p>
                {current.badge ? (
                  <V4Badge tone={current.badgeTone ?? "info"}>{current.badge}</V4Badge>
                ) : null}
              </div>
              <p className="mt-3 flex-1 overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed text-(--qs-text-2)">
                {current.body}
              </p>
              {current.meta ? (
                <p className="mt-3 font-mono text-[11px] text-(--qs-text-3)">{current.meta}</p>
              ) : null}
              {current.footer ? (
                <div className="v4-dream-cycle-card-actions border-t border-(--qs-border) pt-3">{current.footer}</div>
              ) : null}
            </article>
          ) : null}
        </div>
      )}
    </div>
  );
}
