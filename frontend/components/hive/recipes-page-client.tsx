"use client";

import Link from "next/link";
import { DownloadIcon, Loader2Icon, SearchIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import {
  RecipeCosineThresholdBanner,
  RecipeSemanticHitCard,
} from "@/components/hive/recipe-cosine-match-panel";
import { RecipeMarketplaceBetaPanel } from "@/components/hive/recipe-marketplace-beta-panel";
import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge, V4Card, V4CardHeader, V4Chip, V4PageCanvas } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { RecipeMatchConfigPayload, RecipeRow, RecipeSemanticHit, SkillExportResponse } from "@/lib/hive-types";
import { DEFAULT_RECIPE_MATCH_CONFIG } from "@/lib/recipe-match-utils";
import { downloadSkillExportBundle } from "@/lib/skill-export-utils";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";
import { cn } from "@/lib/utils";

interface RecipesPageClientProps {
  readonly showHeader?: boolean;
}

/** Verified catalog + semantic recall + tag facets — Hive Control V4. */
export function RecipesPageClient({ showHeader = true }: RecipesPageClientProps): JSX.Element {
  const [catalog, setCatalog] = useState<RecipeRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [needle, setNeedle] = useState("");
  const [debounced, setDebounced] = useState("");
  const [semanticHits, setSemanticHits] = useState<RecipeSemanticHit[]>([]);
  const [matchConfig, setMatchConfig] = useState<RecipeMatchConfigPayload>(DEFAULT_RECIPE_MATCH_CONFIG);
  const [searchBusy, setSearchBusy] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedPatterns, setSelectedPatterns] = useState<string[]>([]);
  const [exportBusyId, setExportBusyId] = useState<string | null>(null);

  const exportRecipe = useCallback(async (recipeId: string, recipeName: string) => {
    setExportBusyId(recipeId);
    try {
      const bundle = await hivePostJson<SkillExportResponse>(`recipes/${recipeId}/export-skill`, {});
      await downloadSkillExportBundle(bundle);
      toast.success(`Exported ${recipeName}`, {
        description: "Skill bundle downloaded (SKILL.md + HIVE.md).",
      });
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Skill export failed.");
    } finally {
      setExportBusyId(null);
    }
  }, []);

  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(needle.trim()), 350);
    return () => window.clearTimeout(t);
  }, [needle]);

  useEffect(() => {
    let cancelled = false;
    void hiveGet<RecipeRow[]>("recipes?verified_only=true&limit=120")
      .then((rows) => {
        if (!cancelled) {
          setCatalog(rows);
          setErr(null);
        }
      })
      .catch((e) => {
        if (!cancelled) setErr(e instanceof HiveApiError ? e.message : "Recipe catalog unavailable.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    void hiveGet<RecipeMatchConfigPayload>("recipes/match-config")
      .then((cfg) => {
        if (!cancelled) setMatchConfig(cfg);
      })
      .catch(() => {
        /* keep DEFAULT_RECIPE_MATCH_CONFIG */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!debounced) {
      setSemanticHits([]);
      return;
    }
    let cancelled = false;
    setSearchBusy(true);
    void hiveGet<RecipeSemanticHit[]>(`recipes/search?q=${encodeURIComponent(debounced)}&limit=24`)
      .then((hits) => {
        if (!cancelled) setSemanticHits(hits);
      })
      .catch(() => {
        if (!cancelled) setSemanticHits([]);
      })
      .finally(() => {
        if (!cancelled) setSearchBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debounced]);

  const allTags = useMemo(() => {
    const s = new Set<string>();
    for (const r of catalog) {
      for (const t of r.topic_tags ?? []) {
        if (t.trim()) s.add(t.trim());
      }
    }
    return [...s].sort((a, b) => a.localeCompare(b));
  }, [catalog]);

  const allPatterns = useMemo(() => {
    const s = new Set<string>();
    for (const r of catalog) {
      for (const label of r.pattern_labels ?? r.pattern_tags ?? []) {
        if (label.trim()) s.add(label.trim());
      }
    }
    return [...s].sort((a, b) => a.localeCompare(b));
  }, [catalog]);

  const toggleTag = useCallback((tag: string) => {
    setSelectedTags((prev) => (prev.includes(tag) ? prev.filter((x) => x !== tag) : [...prev, tag]));
  }, []);

  const togglePattern = useCallback((pattern: string) => {
    setSelectedPatterns((prev) => (prev.includes(pattern) ? prev.filter((x) => x !== pattern) : [...prev, pattern]));
  }, []);

  const filteredCatalog = useMemo(() => {
    return catalog.filter((r) => {
      const tagsOk = !selectedTags.length || selectedTags.every((t) => (r.topic_tags ?? []).includes(t));
      const labels = r.pattern_labels ?? r.pattern_tags ?? [];
      const patternsOk = !selectedPatterns.length || selectedPatterns.every((p) => labels.includes(p));
      return tagsOk && patternsOk;
    });
  }, [catalog, selectedTags, selectedPatterns]);

  const showingSemantic = Boolean(debounced);

  const catalogPageSize = useGridTwoRowPageSize();
  const catalogResetKey = `${selectedTags.join(",")}|${selectedPatterns.join(",")}|${catalogPageSize}`;
  const catalogPagination = usePaginatedSlice(filteredCatalog, catalogPageSize, catalogResetKey);
  const semanticPagination = usePaginatedSlice(semanticHits, catalogPageSize, `${debounced}|${catalogPageSize}`);

  const recipeCard = (recipe: RecipeRow) => (
    <article key={recipe.id} className={cn("v4-dream-cycle-card flex h-full flex-col gap-4 transition")}>
      <div className="flex items-start justify-between gap-3">
        <V4Badge tone={recipe.verified_at ? "ok" : "warn"}>
          {recipe.verified_at ? "verified" : "draft"}
        </V4Badge>
        <V4Badge tone="gold">★ wins {recipe.success_count ?? 0}</V4Badge>
      </div>
      <div>
        <h2 className="text-xl font-semibold text-(--qs-text)">{recipe.name}</h2>
        {recipe.orchestration_template ? (
          <p className="mt-1 text-xs uppercase tracking-wide text-cyan">
            {recipe.orchestration_template.replaceAll("_", " ")}
          </p>
        ) : null}
        {(recipe.pattern_labels ?? recipe.pattern_tags ?? []).length ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {(recipe.pattern_labels ?? recipe.pattern_tags ?? []).map((p) => (
              <V4Badge key={p} tone="info">
                {p}
              </V4Badge>
            ))}
          </div>
        ) : null}
        {(recipe.topic_tags ?? []).length ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {(recipe.topic_tags ?? []).map((t) => (
              <V4Chip key={t} type="span">
                #{t}
              </V4Chip>
            ))}
          </div>
        ) : null}
      </div>
      <dl className="v4-recipe-card-stats mt-auto grid grid-cols-3 gap-2 text-sm">
        <div>
          <dt className="v4-field-label">Fails</dt>
          <dd className="mt-1 tabular-nums text-(--qs-text)">{recipe.fail_count ?? 0}</dd>
        </div>
        <div>
          <dt className="v4-field-label">Avg pollen</dt>
          <dd className="mt-1 tabular-nums text-pollen">{Math.round(recipe.avg_pollen_earned ?? 0)}</dd>
        </div>
        <div>
          <dt className="v4-field-label">ID</dt>
          <dd className="mt-1 truncate font-mono text-[10px] text-(--qs-text-3)">{recipe.id.slice(0, 8)}…</dd>
        </div>
      </dl>
      <div className="v4-dream-cycle-card-actions">
        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm"
          disabled={exportBusyId === recipe.id}
          onClick={() => void exportRecipe(recipe.id, recipe.name)}
        >
          {exportBusyId === recipe.id ? (
            <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden />
          ) : (
            <DownloadIcon className="h-3.5 w-3.5" aria-hidden />
          )}
          Export skill
        </button>
      </div>
    </article>
  );

  return (
    <V4PageCanvas className="gap-6">
      {showHeader ? (
        <HivePageHeader
          title="Recipe Library"
          subtitle="Verified workflows · Chroma semantic recall · topic + pattern stack facets"
          actions={
            <Link href="/tasks/new" className="qs-btn qs-btn--primary qs-btn--sm">
              Run mission
            </Link>
          }
        />
      ) : (
        <V4Card>
          <V4CardHeader
            title="Saved recipes"
            description="Verified workflow catalog with semantic recall."
            actions={
              <Link href="/tasks/new" className="qs-btn qs-btn--primary qs-btn--sm">
                Run mission
              </Link>
            }
          />
        </V4Card>
      )}

      <RecipeMarketplaceBetaPanel />

      <V4Card>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="relative flex-1">
            <SearchIcon
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-(--qs-text-3)"
              aria-hidden
            />
            <input
              type="search"
              value={needle}
              onChange={(e) => setNeedle(e.target.value)}
              placeholder="Semantic search (natural language)…"
              className="qs-input min-h-11 w-full pl-10"
            />
            {searchBusy ? (
              <Loader2Icon
                className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-pollen"
                aria-hidden
              />
            ) : null}
          </div>
          <p className="hidden text-xs text-(--qs-text-3) lg:block lg:max-w-xs lg:text-right">
            Desktop: keep search + catalog visible together. Mobile: scroll tags → grid.
          </p>
        </div>

        <div className="v4-learning-panel mt-5">
          <p className="v4-field-label mb-2">Topic tags</p>
          <div className="v4-chip-scroll md:flex-wrap md:overflow-visible">
            {allTags.map((tag) => {
              const on = selectedTags.includes(tag);
              return (
                <V4Chip key={tag} active={on} onClick={() => toggleTag(tag)}>
                  #{tag}
                </V4Chip>
              );
            })}
            {!allTags.length ? <span className="text-xs text-(--qs-text-3)">No tags in catalog slice.</span> : null}
          </div>

          <p className="v4-field-label mb-2 mt-4">Agentic patterns</p>
          <div className="v4-chip-scroll md:flex-wrap md:overflow-visible">
            {allPatterns.map((pattern) => {
              const on = selectedPatterns.includes(pattern);
              return (
                <V4Chip key={pattern} active={on} onClick={() => togglePattern(pattern)}>
                  {pattern}
                </V4Chip>
              );
            })}
            {!allPatterns.length ? (
              <span className="text-xs text-(--qs-text-3)">Pattern stacks appear after orchestration recipes are tagged.</span>
            ) : null}
          </div>
        </div>
      </V4Card>

      {err ? (
        <p className="rounded-xl border border-(--qs-red)/35 bg-(--qs-red)/10 px-4 py-3 text-sm text-(--qs-red)">{err}</p>
      ) : null}

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading catalog…
        </p>
      ) : null}

      <V4Card>
        <V4CardHeader
          as="h2"
          title={showingSemantic ? "Semantic hits" : `Catalog · ${filteredCatalog.length} recipes`}
          description={showingSemantic ? "Chroma cosine matches for your query." : "Verified recipes from the hive catalog."}
        />

        {showingSemantic ? (
          <ViewportBoundedPanel
            className="v4-recipe-catalog-panel"
            footer={
              <ListPaginator
                page={semanticPagination.page}
                totalPages={semanticPagination.totalPages}
                totalItems={semanticPagination.totalItems}
                pageSize={catalogPageSize}
                onPageChange={semanticPagination.setPage}
              />
            }
          >
            <div className="flex flex-col gap-4">
              <RecipeCosineThresholdBanner config={matchConfig} hitCount={semanticHits.length} />
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {semanticPagination.slice.map((hit) => (
                  <RecipeSemanticHitCard key={hit.chroma_document_id} hit={hit} config={matchConfig} />
                ))}
              </div>
            </div>
          </ViewportBoundedPanel>
        ) : (
          <ViewportBoundedPanel
            className="v4-recipe-catalog-panel"
            footer={
              <ListPaginator
                page={catalogPagination.page}
                totalPages={catalogPagination.totalPages}
                totalItems={catalogPagination.totalItems}
                pageSize={catalogPageSize}
                onPageChange={catalogPagination.setPage}
              />
            }
          >
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {catalogPagination.slice.map((recipe) => recipeCard(recipe))}
            </div>
          </ViewportBoundedPanel>
        )}

        {!loading && !showingSemantic && filteredCatalog.length === 0 ? (
          <p className="v4-dream-empty mt-4">No recipes match selected tags — clear chips or widen catalog limits.</p>
        ) : null}
        {showingSemantic && !semanticHits.length && !searchBusy ? (
          <p className="v4-dream-empty mt-4">No semantic hits — tweak wording.</p>
        ) : null}
      </V4Card>
    </V4PageCanvas>
  );
}
