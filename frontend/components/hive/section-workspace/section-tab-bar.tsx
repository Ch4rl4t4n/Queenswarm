"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface SectionTab {
  id: string;
  label: string;
  /** Optional count badge (e.g. pending approvals). */
  badge?: number;
  /** Optional inline hint `(i)` rendered after the label. */
  hint?: ReactNode;
  /** Hide this tab without removing it from the list. */
  hidden?: boolean;
}

export interface SectionTabBarProps {
  tabs: SectionTab[];
  active: string;
  onSelect: (id: string) => void;
  className?: string;
  ariaLabel?: string;
}

/**
 * Sub-section menu bar (the "menu bar danej sekcie") — horizontal, scrollable.
 *
 * Lives inside the canvas, not a global top bar, so it never violates the
 * desktop "sidebar + canvas only" rule.
 */
export function SectionTabBar({
  tabs,
  active,
  onSelect,
  className,
  ariaLabel = "Podsekcie",
}: SectionTabBarProps): JSX.Element {
  const visible = tabs.filter((tab) => !tab.hidden);
  // Hint is an interactive popover (a <button>): render it as a sibling of the
  // tab buttons, never nested inside one (invalid DOM / hydration error).
  const activeHint = visible.find((tab) => tab.id === active)?.hint ?? null;
  return (
    <nav aria-label={ariaLabel} className={cn("v4-chip-scroll flex items-center gap-1.5", className)}>
      {visible.map((tab) => {
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onSelect(tab.id)}
            aria-current={isActive ? "page" : undefined}
            data-testid={`section-tab-${tab.id}`}
            className={cn(
              "qs-btn qs-btn--ghost qs-btn--sm min-h-[44px] shrink-0 gap-1.5",
              isActive && "border-pollen/50 text-pollen",
            )}
          >
            <span>{tab.label}</span>
            {typeof tab.badge === "number" && tab.badge > 0 ? (
              <span
                className={cn(
                  "inline-flex min-w-5 items-center justify-center rounded-full px-1.5 font-mono text-[10px]",
                  isActive ? "bg-pollen/20 text-pollen" : "bg-(--qs-border)/40 text-(--qs-text-3)",
                )}
              >
                {tab.badge}
              </span>
            ) : null}
          </button>
        );
      })}
      {activeHint ? <span className="shrink-0">{activeHint}</span> : null}
    </nav>
  );
}
