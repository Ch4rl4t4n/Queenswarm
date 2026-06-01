"use client";

import type { ReactNode } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { cn } from "@/lib/utils";

export interface HubCatalogCategory {
  id: string;
  label: string;
  count: number;
  /** Show green dot when category has provisioned / active items. */
  showDot?: boolean;
}

export interface HubCatalogStat {
  label: string;
  tone: "info" | "ok" | "warn" | "gold";
}

export interface HubCategoryCatalogShellProps {
  title: string;
  description: ReactNode;
  hint?: ReactNode;
  stats?: HubCatalogStat[];
  error?: string | null;
  refreshBusy?: boolean;
  onRefresh?: () => void;
  categories: HubCatalogCategory[];
  openCategory: string | null;
  onCategoryChange: (categoryId: string) => void;
  sectionLabel: string;
  sectionCount: number;
  /** Plural noun after count — default `items`. */
  sectionItemLabel?: string;
  children: ReactNode;
  className?: string;
  embedded?: boolean;
}

/** Shared Integrations hub catalog chrome — category bubbles + section header + grid slot. */
export function HubCategoryCatalogShell({
  title,
  description,
  hint,
  stats,
  error,
  refreshBusy = false,
  onRefresh,
  categories,
  openCategory,
  onCategoryChange,
  sectionLabel,
  sectionCount,
  sectionItemLabel = "items",
  children,
  className,
  embedded = false,
}: HubCategoryCatalogShellProps): JSX.Element {
  const body = (
    <>
      {error ? (
        <p className="rounded-xl border border-magenta/35 bg-magenta/10 px-3 py-2 text-xs text-magenta" role="status">
          {error}
        </p>
      ) : null}

      {stats && stats.length > 0 ? (
        <div className="hub-catalog-stats flex flex-wrap items-center gap-2">
          {stats.map((stat) => (
            <V4Badge key={stat.label} tone={stat.tone}>
              {stat.label}
            </V4Badge>
          ))}
        </div>
      ) : null}

      <div className="hub-catalog-body min-w-0 space-y-4">
        <div className="hub-category-bubble-grid" role="tablist" aria-label="Catalog categories">
          {categories.map((category) => {
            const active = openCategory === category.id;
            return (
              <button
                key={category.id}
                type="button"
                role="tab"
                aria-selected={active}
                className={cn("hub-category-bubble", active && "hub-category-bubble--active")}
                onClick={() => onCategoryChange(category.id)}
              >
                <span className="hub-category-bubble__label">{category.label}</span>
                <V4Badge tone={active ? "gold" : "info"}>{category.count}</V4Badge>
                {category.showDot ? (
                  <span className="hub-category-bubble__dot" aria-hidden />
                ) : null}
              </button>
            );
          })}
        </div>

        {openCategory ? (
          <div className="hub-catalog-section min-w-0 space-y-3">
            <div className="hub-catalog-section-head flex flex-wrap items-center gap-2">
              <p className="hub-catalog-section-head__label">{sectionLabel.toUpperCase()}</p>
              <V4Badge tone="info">
                {sectionCount} {sectionCount === 1 ? sectionItemLabel.replace(/s$/, "") : sectionItemLabel}
              </V4Badge>
            </div>
            {children}
          </div>
        ) : null}
      </div>
    </>
  );

  if (embedded) {
    return (
      <div className={cn("hub-catalog-shell hub-catalog-shell--embedded space-y-4", className)}>
        <V4CardHeader
          title={title}
          description={description}
          hint={hint}
          actions={onRefresh ? <HiveRefreshButton busy={refreshBusy} onClick={() => void onRefresh()} /> : undefined}
        />
        {body}
      </div>
    );
  }

  return (
    <V4Card className={cn("hub-catalog-shell space-y-4", className)}>
      <V4CardHeader
        title={title}
        description={description}
        hint={hint}
        actions={onRefresh ? <HiveRefreshButton busy={refreshBusy} onClick={() => void onRefresh()} /> : undefined}
      />
      {body}
    </V4Card>
  );
}
