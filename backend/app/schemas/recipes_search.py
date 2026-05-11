"""Chroma-backed semantic search responses for Recipe Library routing."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.recipes_catalog import RecipeCatalogItem


class RecipeSemanticHit(BaseModel):
    """One Chroma cosine hit optionally merged with Postgres catalog metadata."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    chroma_document_id: str = Field(description="Stable Chroma embedding row id.")
    similarity: float = Field(ge=0.0, le=1.0, description="1 - cosine distance.")
    distance: float | None = Field(
        default=None,
        description="Raw Chroma distance when provided by the cluster.",
    )
    document_preview: str = Field(
        default="",
        description="Truncated workflow text surfaced for dashboards.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    postgres_recipe_id: uuid.UUID | None = Field(
        default=None,
        description="Resolved Recipe primary key when embedding metadata declares it.",
    )
    postgres_row: RecipeCatalogItem | None = Field(
        default=None,
        description="Joined leaderboard row when a UUID was resolved.",
    )


__all__ = ["RecipeSemanticHit"]
