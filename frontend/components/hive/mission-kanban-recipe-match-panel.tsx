"use client";

import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { RecipeCosineThresholdBanner, RecipeSemanticHitRow } from "@/components/hive/recipe-cosine-match-panel";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { DEFAULT_RECIPE_MATCH_CONFIG } from "@/lib/recipe-match-utils";
import type { RecipeMatchConfigPayload, RecipeSemanticHit } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface MissionKanbanRecipeMatchPayload {
  enabled: boolean;
  query: string;
  hits: RecipeSemanticHit[];
  match_config: RecipeMatchConfigPayload;
  operator_hint?: string;
}

interface MissionKanbanRecipeMatchPanelProps {
  query: string;
  selectedRecipeId: string | null;
  onSelectRecipe: (recipeId: string | null) => void;
  enrichRecipes: boolean;
  onEnrichRecipesChange: (value: boolean) => void;
}

/** FP1 — Cosine recipe matching for Mission Kanban triage dispatch. */
export function MissionKanbanRecipeMatchPanel({
  query,
  selectedRecipeId,
  onSelectRecipe,
  enrichRecipes,
  onEnrichRecipesChange,
}: MissionKanbanRecipeMatchPanelProps): JSX.Element | null {
  const [payload, setPayload] = useState<MissionKanbanRecipeMatchPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    const trimmed = query.trim();
    if (trimmed.length < 8) {
      setPayload(null);
      setErr(null);
      return;
    }
    setLoading(true);
    try {
      const data = await hiveGet<MissionKanbanRecipeMatchPayload>(
        `operator/mission-kanban/recipe-match?q=${encodeURIComponent(trimmed)}&limit=5`,
      );
      setPayload(data);
      setErr(null);
    } catch (e) {
      setPayload(null);
      setErr(e instanceof HiveApiError ? e.message : "Recipe match unavailable.");
    } finally {
      setLoading(false);
    }
  }, [query]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 400);
    return () => window.clearTimeout(timer);
  }, [load]);

  if (query.trim().length < 8) {
    return null;
  }

  const matchConfig = payload?.match_config ?? DEFAULT_RECIPE_MATCH_CONFIG;
  const hits = payload?.hits ?? [];

  return (
    <div data-testid="mission-kanban-recipe-match-panel">
    <V4Card className="border-cyan/20 bg-cyan/5">
      <V4CardHeader
        title="Recipe match"
        description="FP1 — cosine-ranked verified workflows for dispatch."
        actions={
          enrichRecipes ? (
            <V4Badge tone="ok">Chroma on</V4Badge>
          ) : (
            <V4Badge tone="warn">Chroma off</V4Badge>
          )
        }
      />
      <div className="space-y-3 px-4 pb-4">
        <label className="flex items-center gap-2 text-xs text-(--qs-text-2)">
          <input
            type="checkbox"
            checked={enrichRecipes}
            onChange={(e) => onEnrichRecipesChange(e.target.checked)}
            className="rounded border-cyan/40"
          />
          Enrich dispatch from Recipe Library (cosine ≥ gate)
        </label>

        {loading ? (
          <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Matching recipes…
          </p>
        ) : null}

        {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

        {!loading && payload?.enabled && hits.length > 0 ? (
          <>
            <RecipeCosineThresholdBanner config={matchConfig} hitCount={hits.length} />
            <ul className="space-y-2">
              {hits.map((hit) => {
                const recipeId = hit.postgres_recipe_id ?? hit.postgres_row?.id;
                const selected = recipeId != null && selectedRecipeId === String(recipeId);
                return (
                  <li key={hit.chroma_document_id} className="flex flex-col gap-2 sm:flex-row sm:items-start">
                    <div className="min-w-0 flex-1">
                      <RecipeSemanticHitRow hit={hit} config={matchConfig} />
                    </div>
                    {recipeId ? (
                      <button
                        type="button"
                        className={cn(
                          "qs-btn qs-btn--sm shrink-0",
                          selected ? "qs-btn--cyan" : "qs-btn--ghost",
                        )}
                        onClick={() =>
                          onSelectRecipe(selected ? null : String(recipeId))
                        }
                      >
                        {selected ? "Selected" : "Use on dispatch"}
                      </button>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </>
        ) : null}

        {!loading && !err && payload?.enabled && hits.length === 0 ? (
          <p className="text-xs text-(--qs-text-3)">
            {payload.operator_hint ?? "No semantic recipe hits yet — dispatch still uses breaker decomposition."}
          </p>
        ) : null}
      </div>
    </V4Card>
    </div>
  );
}
