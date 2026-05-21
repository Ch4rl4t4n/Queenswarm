/** Recipe cosine matching helpers — aligned with backend match-config. */

import type { RecipeMatchConfigPayload, RecipeSemanticHit } from "@/lib/hive-types";

export const DEFAULT_RECIPE_MATCH_CONFIG: RecipeMatchConfigPayload = {
  match_threshold: 0.85,
  min_search_similarity: 0,
  hybrid_scoring_enabled: true,
  hybrid_vector_weight: 0.85,
  hybrid_graph_weight: 0.15,
};

export function formatSimilarityPct(similarity: number): string {
  return `${(similarity * 100).toFixed(1)}%`;
}

export function isRecipeMatchEligible(similarity: number, threshold: number): boolean {
  return similarity >= threshold;
}

export function recipeMatchTone(
  similarity: number,
  threshold: number,
): "ok" | "warn" | "info" {
  if (similarity >= threshold) {
    return "ok";
  }
  if (similarity >= threshold * 0.9) {
    return "warn";
  }
  return "info";
}

export function primarySimilarity(hit: RecipeSemanticHit): number {
  return hit.similarity;
}

export function vectorSimilarity(hit: RecipeSemanticHit): number | null {
  if (typeof hit.vector_similarity === "number") {
    return hit.vector_similarity;
  }
  return null;
}

export function hybridSummary(config: RecipeMatchConfigPayload): string {
  if (!config.hybrid_scoring_enabled) {
    return "Vector cosine only";
  }
  const vectorPct = Math.round(config.hybrid_vector_weight * 100);
  const graphPct = Math.round(config.hybrid_graph_weight * 100);
  return `Hybrid ${vectorPct}% vector · ${graphPct}% graph`;
}
