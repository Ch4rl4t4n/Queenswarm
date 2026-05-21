"""Recipe Library semantic matching configuration for operator UI."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings


class RecipeMatchConfigResponse(BaseModel):
    """Public imitation-engine cosine gate surfaced to dashboards."""

    model_config = ConfigDict(extra="ignore")

    match_threshold: float = Field(
        ge=0.0,
        le=1.0,
        description="Minimum hybrid/vector score for workflow auto-match (default 0.85).",
    )
    min_search_similarity: float = Field(
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity returned by GET /recipes/search.",
    )
    hybrid_scoring_enabled: bool
    hybrid_vector_weight: float = Field(ge=0.0, le=1.0)
    hybrid_graph_weight: float = Field(ge=0.0, le=1.0)


def build_recipe_match_config() -> RecipeMatchConfigResponse:
    """Build match-config payload from runtime settings."""

    return RecipeMatchConfigResponse(
        match_threshold=float(settings.recipe_library_match_threshold),
        min_search_similarity=float(settings.recipe_chroma_min_similarity),
        hybrid_scoring_enabled=bool(settings.recipe_hybrid_scoring_enabled),
        hybrid_vector_weight=float(settings.recipe_hybrid_vector_weight),
        hybrid_graph_weight=float(settings.recipe_hybrid_graph_weight),
    )


__all__ = ["RecipeMatchConfigResponse", "build_recipe_match_config"]
