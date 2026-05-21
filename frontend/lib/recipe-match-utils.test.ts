import { describe, expect, it } from "vitest";

import {
  formatSimilarityPct,
  hybridSummary,
  isRecipeMatchEligible,
  recipeMatchTone,
} from "@/lib/recipe-match-utils";
import type { RecipeMatchConfigPayload } from "@/lib/hive-types";

describe("recipe-match-utils", () => {
  it("marks similarity at or above 0.85 as eligible", () => {
    expect(isRecipeMatchEligible(0.85, 0.85)).toBe(true);
    expect(isRecipeMatchEligible(0.84, 0.85)).toBe(false);
  });

  it("formats similarity as percentage", () => {
    expect(formatSimilarityPct(0.853)).toBe("85.3%");
  });

  it("returns warn tone near threshold", () => {
    expect(recipeMatchTone(0.77, 0.85)).toBe("warn");
    expect(recipeMatchTone(0.86, 0.85)).toBe("ok");
  });

  it("summarizes hybrid weights", () => {
    const config: RecipeMatchConfigPayload = {
      match_threshold: 0.85,
      min_search_similarity: 0,
      hybrid_scoring_enabled: true,
      hybrid_vector_weight: 0.85,
      hybrid_graph_weight: 0.15,
    };
    expect(hybridSummary(config)).toContain("Hybrid");
  });
});
