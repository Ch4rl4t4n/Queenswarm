"use client";

import { RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { HubCategoryCatalogShell } from "@/components/connectors/hub-category-catalog-shell";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";
import {
  extractPhase3FromCatalog,
  orderedPhase3Categories,
  phase3CategoryLabel,
  phase3CategoryShortLabel,
} from "@/lib/connectors-phase3";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";
import type { IntegrationsTab } from "@/lib/integrations-routes";
import { cn } from "@/lib/utils";

export type IntegrationCardStatus = "connected" | "error" | "rate_limited";

export type IntegrationCardKind = "plugin" | "connector" | "external" | "system";

export interface IntegrationCard {
  id: string;
  title: string;
  meta: string;
  description: string;
  status: IntegrationCardStatus;
  kind: IntegrationCardKind;
  targetTab: IntegrationsTab;
  slug?: string;
  iconKey: string;
  categoryKey: string;
}

function statusTone(status: IntegrationCardStatus): "ok" | "warn" | "err" {
  if (status === "connected") return "ok";
  if (status === "rate_limited") return "warn";
  return "err";
}

function statusLabel(status: IntegrationCardStatus): string {
  if (status === "connected") return "Connected";
  if (status === "rate_limited") return "Rate limited";
  return "Needs attention";
}

function categoryLabel(categoryKey: string): string {
  if (categoryKey === "plugins") return "Plugins";
  if (categoryKey === "external") return "External projects";
  if (categoryKey === "connectors_other") return "Other connectors";
  return phase3CategoryLabel(categoryKey);
}

function categoryShortLabel(categoryKey: string): string {
  if (categoryKey === "plugins") return "Plugins";
  if (categoryKey === "external") return "External";
  if (categoryKey === "connectors_other") return "Other";
  return phase3CategoryShortLabel(categoryKey);
}

function sectionItemLabel(categoryKey: string): string {
  if (categoryKey === "plugins") return "plugins";
  if (categoryKey === "external") return "projects";
  return "integrations";
}

interface ActiveIntegrationsPanelProps {
  cards: IntegrationCard[];
  healthyCount: number;
  refreshing: boolean;
  retryingId: string | null;
  hasHubTab: boolean;
  hasMarketplaceTab: boolean;
  onRefresh: () => void | Promise<void>;
  onRetry: (card: IntegrationCard) => void | Promise<void>;
  onOpen: (tab: IntegrationsTab) => void;
  onOpenHub: () => void;
  onOpenMarketplace: () => void;
}

/** Active integrations — Phase 3 catalog grid with category bubbles (mobile / tablet / desktop). */
export function ActiveIntegrationsPanel({
  cards,
  healthyCount,
  refreshing,
  retryingId,
  hasHubTab,
  hasMarketplaceTab,
  onRefresh,
  onRetry,
  onOpen,
  onOpenHub,
  onOpenMarketplace,
}: ActiveIntegrationsPanelProps): JSX.Element {
  const [slugCategoryMap, setSlugCategoryMap] = useState<Map<string, string>>(new Map());

  useEffect(() => {
    let cancelled = false;
    void hiveGet<unknown>("connectors/catalog")
      .then((body) => {
        if (cancelled) return;
        const slice = extractPhase3FromCatalog(body);
        const map = new Map<string, string>();
        for (const tpl of slice?.templates ?? []) {
          map.set(tpl.suggested_slug.trim().toLowerCase(), tpl.category);
        }
        setSlugCategoryMap(map);
      })
      .catch(() => {
        if (!cancelled) setSlugCategoryMap(new Map());
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const cardsWithCategory = useMemo(
    () =>
      cards.map((card) => {
        if (card.kind === "plugin") {
          return { ...card, categoryKey: "plugins" };
        }
        if (card.kind === "external") {
          return { ...card, categoryKey: "external" };
        }
        const slug = card.slug?.trim().toLowerCase() ?? "";
        const mapped = slugCategoryMap.get(slug);
        return { ...card, categoryKey: mapped ?? "connectors_other" };
      }),
    [cards, slugCategoryMap],
  );

  const grouped = useMemo(() => {
    const map: Record<string, IntegrationCard[]> = {};
    for (const card of cardsWithCategory) {
      const bucket = map[card.categoryKey] ?? [];
      bucket.push(card);
      map[card.categoryKey] = bucket;
    }
    return map;
  }, [cardsWithCategory]);

  const categoryOrder = useMemo(() => {
    const connectorCats = orderedPhase3Categories(
      Object.fromEntries(
        Object.entries(grouped).filter(
          ([key]) => key !== "plugins" && key !== "external" && key !== "connectors_other",
        ),
      ),
    );
    const tail: string[] = [];
    if (grouped.connectors_other?.length) tail.push("connectors_other");
    if (grouped.plugins?.length) tail.push("plugins");
    if (grouped.external?.length) tail.push("external");
    return [...connectorCats, ...tail];
  }, [grouped]);

  const [openCategory, setOpenCategory] = useState<string | null>(categoryOrder[0] ?? null);

  useEffect(() => {
    if (openCategory && categoryOrder.includes(openCategory)) {
      return;
    }
    setOpenCategory(categoryOrder[0] ?? null);
  }, [categoryOrder, openCategory]);

  const categoryCards = openCategory ? (grouped[openCategory] ?? []) : [];
  const pageSize = useGridTwoRowPageSize({ columns: 2 });
  const pagination = usePaginatedSlice(
    categoryCards,
    pageSize,
    `${openCategory}|${pageSize}|${categoryCards.length}|${cards.length}`,
  );

  const catalogCategories = useMemo(
    () =>
      categoryOrder.map((categoryKey) => ({
        id: categoryKey,
        label: categoryShortLabel(categoryKey),
        count: grouped[categoryKey]?.length ?? 0,
        showDot: (grouped[categoryKey] ?? []).some((card) => card.status === "connected"),
      })),
    [categoryOrder, grouped],
  );

  const activeCount = cards.filter((card) => card.status === "connected").length;

  if (!cards.length) {
    return (
      <HubCategoryCatalogShell
        embedded
        className="active-integrations-card"
        title="Active integrations"
        description="Unified health snapshot across hub, bridges, and plugins."
        hint={sectionHintNode("integrationsActive")}
        stats={[{ label: "0 healthy", tone: "warn" }]}
        refreshBusy={refreshing}
        onRefresh={onRefresh}
        categories={[]}
        openCategory={null}
        onCategoryChange={() => undefined}
        sectionLabel="Integrations"
        sectionCount={0}
        sectionItemLabel="integrations"
      >
        <div className="v4-learning-panel flex flex-col items-center gap-3 p-6 text-center">
          <p className="text-sm text-(--qs-text-3)">
            No integrations connected yet. Install a marketplace template or provision a connector in the hub.
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {hasHubTab ? (
              <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" onClick={onOpenHub}>
                Open connector hub
              </button>
            ) : null}
            {hasMarketplaceTab ? (
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={onOpenMarketplace}>
                Browse marketplace
              </button>
            ) : null}
          </div>
        </div>
      </HubCategoryCatalogShell>
    );
  }

  return (
    <HubCategoryCatalogShell
      embedded
      className="active-integrations-card"
      title="Active integrations"
      description="Unified health snapshot across hub, bridges, and plugins."
      hint={sectionHintNode("integrationsActive")}
      stats={[
        { label: `${healthyCount} / ${cards.length} healthy`, tone: "ok" },
        { label: `${activeCount} connected`, tone: "info" },
      ]}
      refreshBusy={refreshing}
      onRefresh={onRefresh}
      categories={catalogCategories}
      openCategory={openCategory}
      onCategoryChange={setOpenCategory}
      sectionLabel={openCategory ? categoryLabel(openCategory) : "Integrations"}
      sectionCount={categoryCards.length}
      sectionItemLabel={openCategory ? sectionItemLabel(openCategory) : "integrations"}
    >
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
          {pagination.slice.map((card) => (
            <article key={card.id} className="hub-catalog-card active-integration-card">
              <header className="hub-catalog-card__head">
                <p className="hub-catalog-card__title">{card.title}</p>
                <p className="hub-catalog-card__summary">{card.description}</p>
              </header>
              <div className="hub-catalog-card__manifest">
                <p className="hub-catalog-card__manifest-label">Integration status</p>
                <p className="hub-catalog-card__manifest-meta">{card.meta}</p>
                <div className="hub-catalog-card__status-row">
                  <p
                    className={cn(
                      "hub-catalog-card__status",
                      card.status === "connected"
                        ? "hub-catalog-card__status--ok"
                        : "hub-catalog-card__status--pending",
                    )}
                  >
                    {statusLabel(card.status)}
                  </p>
                  <V4Badge tone={statusTone(card.status)}>{card.status}</V4Badge>
                </div>
              </div>
              <footer className="hub-catalog-card__foot">
                <span className="text-[11px] font-mono text-(--qs-text-3)">{card.kind}</span>
                <div className="hub-catalog-card__actions">
                  {card.status === "error" || card.status === "rate_limited" ? (
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
                      disabled={retryingId === card.id}
                      onClick={() => void onRetry(card)}
                    >
                      <RefreshCw className={cn("size-3.5", retryingId === card.id && "animate-spin")} aria-hidden />
                      Retry
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm min-w-[5.5rem]"
                    onClick={() => onOpen(card.targetTab)}
                  >
                    Open
                  </button>
                </div>
              </footer>
            </article>
          ))}
        </div>
      </ViewportBoundedPanel>
    </HubCategoryCatalogShell>
  );
}
