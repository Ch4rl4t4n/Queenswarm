"use client";

import type { JSX } from "react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { HubCategoryCatalogShell } from "@/components/connectors/hub-category-catalog-shell";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import {
  extractPhase3FromCatalog,
  orderedPhase3Categories,
  phase3CategoryLabel,
  phase3CategoryShortLabel,
  type Phase3CatalogSlice,
} from "@/lib/connectors-phase3";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";
import { cn } from "@/lib/utils";

type CostTier = "low" | "medium" | "high";
type LatencyTier = "fast" | "balanced" | "slow";

type ToolFilterId = "all" | "ranked" | "low_cost" | "fast";

interface ToolRegistryRow {
  connector_slug: string;
  connector_display_name: string;
  tool_name: string;
  description: string;
  method: string;
  path: string;
  cost_tier?: CostTier | null;
  latency_tier?: LatencyTier | null;
  score?: number;
  is_active: boolean;
}

interface FeaturedPresetRow {
  source: string;
  id: string;
  slug: string;
  title: string;
  summary: string;
  category: string;
  auth_type: string;
  tool_count: number;
  installed: boolean;
  featured?: boolean;
  mcp_preset?: boolean;
}

interface ToolHubOverviewResponse {
  registry: ToolRegistryRow[];
  featured_presets: FeaturedPresetRow[];
  venice_preset: FeaturedPresetRow | null;
  totals: {
    installed_tools: number;
    active_presets: number;
    featured_count: number;
  };
  goal?: string | null;
}

interface ToolRowView extends ToolRegistryRow {
  categoryKey: string;
}

const TOOL_FILTERS: { id: ToolFilterId; label: string }[] = [
  { id: "all", label: "All tools" },
  { id: "ranked", label: "Ranked" },
  { id: "low_cost", label: "Low cost" },
  { id: "fast", label: "Fast" },
];

function costLabel(tier: CostTier | null | undefined): string {
  if (tier === "low") return "Low cost";
  if (tier === "medium") return "Med cost";
  if (tier === "high") return "High cost";
  return "—";
}

function latencyLabel(tier: LatencyTier | null | undefined): string {
  if (tier === "fast") return "Fast";
  if (tier === "balanced") return "Balanced";
  if (tier === "slow") return "Slow";
  return "—";
}

function costTone(tier: CostTier | null | undefined): "ok" | "warn" | "err" {
  if (tier === "low") return "ok";
  if (tier === "high") return "err";
  return "warn";
}

function latencyTone(tier: LatencyTier | null | undefined): "ok" | "warn" | "err" {
  if (tier === "fast") return "ok";
  if (tier === "slow") return "err";
  return "warn";
}

function matchesToolFilter(row: ToolRegistryRow, filter: ToolFilterId): boolean {
  if (filter === "ranked") return (row.score ?? 0) > 0;
  if (filter === "low_cost") return row.cost_tier === "low";
  if (filter === "fast") return row.latency_tier === "fast";
  return true;
}

interface UnifiedToolHubPanelProps {
  embedded?: boolean;
}

/** Unified Tool Hub — category bubble menu + numbered page grid (no collector deck). */
export function UnifiedToolHubPanel({ embedded = true }: UnifiedToolHubPanelProps): JSX.Element {
  const [overview, setOverview] = useState<ToolHubOverviewResponse | null>(null);
  const [phase3Slice, setPhase3Slice] = useState<Phase3CatalogSlice | null>(null);
  const [goal, setGoal] = useState("");
  const [toolFilter, setToolFilter] = useState<ToolFilterId>("all");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (searchGoal?: string): Promise<void> => {
    setError(null);
    setLoading(true);
    try {
      const query = searchGoal?.trim() ? `?goal=${encodeURIComponent(searchGoal.trim())}` : "";
      const [payload, catalog] = await Promise.all([
        hiveGet<ToolHubOverviewResponse>(`tools/hub/overview${query}`),
        hiveGet<unknown>("connectors/catalog").catch(() => null),
      ]);
      setOverview(payload);
      setPhase3Slice(catalog ? extractPhase3FromCatalog(catalog) : null);
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Tool Hub unavailable.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const venice = overview?.venice_preset ?? null;
  const registry = useMemo(() => overview?.registry ?? [], [overview?.registry]);

  const slugCategoryMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const tpl of phase3Slice?.templates ?? []) {
      map.set(tpl.suggested_slug.trim().toLowerCase(), tpl.category);
    }
    for (const preset of overview?.featured_presets ?? []) {
      if (preset.slug && preset.category) {
        map.set(preset.slug.trim().toLowerCase(), preset.category);
      }
    }
    return map;
  }, [overview?.featured_presets, phase3Slice?.templates]);

  const toolsWithCategory = useMemo((): ToolRowView[] => {
    const needle = goal.trim().toLowerCase();
    return registry
      .filter((row) => {
        if (!needle) return true;
        return (
          row.tool_name.toLowerCase().includes(needle) ||
          row.connector_slug.toLowerCase().includes(needle) ||
          row.connector_display_name.toLowerCase().includes(needle) ||
          row.description.toLowerCase().includes(needle)
        );
      })
      .map((row) => ({
        ...row,
        categoryKey: slugCategoryMap.get(row.connector_slug.trim().toLowerCase()) ?? "connectors_other",
      }));
  }, [goal, registry, slugCategoryMap]);

  const groupedTools = useMemo(() => {
    const grouped: Record<string, ToolRowView[]> = {};
    for (const row of toolsWithCategory) {
      const bucket = grouped[row.categoryKey] ?? [];
      bucket.push(row);
      grouped[row.categoryKey] = bucket;
    }
    for (const key of Object.keys(grouped)) {
      grouped[key]?.sort((a, b) => (b.score ?? 0) - (a.score ?? 0) || a.tool_name.localeCompare(b.tool_name));
    }
    return grouped;
  }, [toolsWithCategory]);

  const categoryOrder = useMemo(() => {
    const connectorCats = orderedPhase3Categories(
      Object.fromEntries(
        Object.entries(groupedTools).filter(([key]) => key !== "connectors_other"),
      ),
    );
    return groupedTools.connectors_other?.length ? [...connectorCats, "connectors_other"] : connectorCats;
  }, [groupedTools]);

  const [openCategory, setOpenCategory] = useState<string | null>(categoryOrder[0] ?? null);

  useEffect(() => {
    if (openCategory && categoryOrder.includes(openCategory)) {
      return;
    }
    setOpenCategory(categoryOrder[0] ?? null);
  }, [categoryOrder, openCategory]);

  useEffect(() => {
    setToolFilter(goal.trim() ? "ranked" : "all");
  }, [goal]);

  const categoryTools = useMemo(() => {
    const base = openCategory ? (groupedTools[openCategory] ?? []) : [];
    return base.filter((row) => matchesToolFilter(row, toolFilter));
  }, [groupedTools, openCategory, toolFilter]);

  const pageSize = useGridTwoRowPageSize({ columns: 2 });
  const pagination = usePaginatedSlice(
    categoryTools,
    pageSize,
    `${openCategory}|${toolFilter}|${goal}|${pageSize}|${categoryTools.length}`,
  );

  const catalogCategories = useMemo(
    () =>
      categoryOrder.map((categoryKey) => ({
        id: categoryKey,
        label: categoryKey === "connectors_other" ? "Other" : phase3CategoryShortLabel(categoryKey),
        count: groupedTools[categoryKey]?.length ?? 0,
        showDot: (groupedTools[categoryKey] ?? []).some((row) => row.is_active),
      })),
    [categoryOrder, groupedTools],
  );

  const filterCounts = useMemo(() => {
    const base = openCategory ? (groupedTools[openCategory] ?? []) : [];
    return {
      all: base.length,
      ranked: base.filter((row) => matchesToolFilter(row, "ranked")).length,
      low_cost: base.filter((row) => matchesToolFilter(row, "low_cost")).length,
      fast: base.filter((row) => matchesToolFilter(row, "fast")).length,
    };
  }, [groupedTools, openCategory]);

  async function installVenice(): Promise<void> {
    if (!venice) return;
    setBusyId(venice.id);
    setError(null);
    try {
      await hivePostJson("tools/marketplace/install", {
        source: venice.source || "phase3_template",
        entry_id: venice.id,
      });
      await load(goal);
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Venice install failed.";
      setError(detail);
    } finally {
      setBusyId(null);
    }
  }

  const categoryLabel =
    openCategory === "connectors_other"
      ? "Other connectors"
      : openCategory
        ? phase3CategoryLabel(openCategory)
        : "Tools";

  return (
    <div className="hub-tool-registry-wrap min-w-0 space-y-4">
      {venice ? (
        <article className="hub-tool-featured qs-bubble--tint-cyan flex flex-col gap-3 rounded-xl border border-cyan/25 bg-cyan/5 p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-cyan">Featured MCP preset</p>
              <p className="text-sm font-semibold text-(--qs-text)">{venice.title}</p>
            </div>
            <V4Badge tone={venice.installed ? "ok" : "warn"}>{venice.installed ? "installed" : "not installed"}</V4Badge>
          </div>
          <p className="text-xs text-(--qs-text-3)">{venice.summary}</p>
          {!venice.installed ? (
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm self-start"
              disabled={busyId === venice.id}
              onClick={() => void installVenice()}
            >
              {busyId === venice.id ? "Installing Venice…" : "Install Venice MCP preset"}
            </button>
          ) : (
            <p className="text-[11px] text-(--qs-green)">Venice connector ready — seal bearer token in Vault and test.</p>
          )}
        </article>
      ) : null}

      <HubCategoryCatalogShell
        embedded={embedded}
        className="hub-tool-registry-card"
        title="Unified Tool Hub"
        description="Orchestrated MCP registry with cost and latency hints — supervisor lanes pick tools by goal overlap."
        hint={sectionHintNode("integrationsHubTools")}
        stats={
          overview
            ? [
                { label: `${overview.totals.installed_tools} active tools`, tone: "info" },
                { label: `${overview.totals.active_presets} installed presets`, tone: "ok" },
              ]
            : undefined
        }
        error={error}
        refreshBusy={loading}
        onRefresh={() => void load(goal)}
        categories={catalogCategories}
        openCategory={openCategory}
        onCategoryChange={setOpenCategory}
        sectionLabel={categoryLabel}
        sectionCount={categoryTools.length}
        sectionItemLabel="tools"
      >
        <div className="hub-tool-registry-toolbar min-w-0 space-y-3">
          <div className="hub-tool-goal-filter flex flex-col gap-3 sm:flex-row sm:items-end">
            <label className="flex min-w-0 flex-1 flex-col gap-1">
              <span className="v4-field-label">Goal filter</span>
              <input
                type="search"
                className="qs-input"
                placeholder="e.g. search knowledge, generate image, TTS briefing"
                value={goal}
                onChange={(event) => setGoal(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void load(goal);
                }}
              />
            </label>
            <button
              type="button"
              className="qs-btn qs-btn--secondary qs-btn--sm shrink-0"
              onClick={() => void load(goal)}
            >
              Rank by goal
            </button>
          </div>

          <div className="hub-tool-filter-row flex flex-wrap gap-2" role="tablist" aria-label="Tool filters">
            {TOOL_FILTERS.map((filter) => {
              const active = toolFilter === filter.id;
              const count = filterCounts[filter.id];
              return (
                <button
                  key={filter.id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  className={cn("hub-category-bubble hub-tool-filter-bubble", active && "hub-category-bubble--active")}
                  onClick={() => setToolFilter(filter.id)}
                >
                  <span className="hub-category-bubble__label">{filter.label}</span>
                  <V4Badge tone={active ? "gold" : "info"}>{count}</V4Badge>
                </button>
              );
            })}
          </div>
        </div>

        {loading && !overview ? (
          <p className="v4-dream-empty">Loading registry…</p>
        ) : categoryTools.length === 0 ? (
          <p className="v4-dream-empty">No tools in this category — adjust goal filter or install a Phase 3 template.</p>
        ) : (
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
              {pagination.slice.map((row) => (
                <article key={`${row.connector_slug}:${row.tool_name}`} className="hub-catalog-card hub-tool-card">
                  <header className="hub-catalog-card__head">
                    <p className="hub-catalog-card__title">{row.tool_name}</p>
                    <p className="hub-catalog-card__summary">{row.description}</p>
                  </header>
                  <div className="hub-catalog-card__manifest">
                    <p className="hub-catalog-card__manifest-label">MCP manifest</p>
                    <p className="hub-catalog-card__manifest-meta">
                      {row.connector_slug}
                      <span aria-hidden> · </span>
                      {row.method} {row.path}
                    </p>
                    <div className="hub-catalog-card__status-row">
                      <p
                        className={cn(
                          "hub-catalog-card__status",
                          row.is_active
                            ? "hub-catalog-card__status--ok"
                            : "hub-catalog-card__status--pending",
                        )}
                      >
                        {row.is_active ? "Live in registry" : "Registered · inactive"}
                      </p>
                      {typeof row.score === "number" && row.score > 0 ? (
                        <V4Badge tone="gold">score {row.score.toFixed(2)}</V4Badge>
                      ) : null}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {row.cost_tier ? <V4Badge tone={costTone(row.cost_tier)}>{costLabel(row.cost_tier)}</V4Badge> : null}
                    {row.latency_tier ? (
                      <V4Badge tone={latencyTone(row.latency_tier)}>{latencyLabel(row.latency_tier)}</V4Badge>
                    ) : null}
                    <V4Badge tone="info">{row.connector_display_name || row.connector_slug}</V4Badge>
                  </div>
                  <footer className="hub-catalog-card__foot">
                    <span className="text-[11px] font-mono text-(--qs-text-3)">{row.connector_slug}</span>
                    <div className="hub-catalog-card__actions">
                      <Link href="/integrations?tab=hub&hubSection=roster" className="qs-btn qs-btn--ghost qs-btn--sm">
                        Roster
                      </Link>
                      <Link
                        href="/integrations?tab=hub&hubSection=templates"
                        className="qs-btn qs-btn--primary qs-btn--sm min-w-[5.5rem]"
                      >
                        Templates
                      </Link>
                    </div>
                  </footer>
                </article>
              ))}
            </div>
          </ViewportBoundedPanel>
        )}
      </HubCategoryCatalogShell>
    </div>
  );
}
