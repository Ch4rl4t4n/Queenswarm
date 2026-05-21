"""Map Recipe ORM rows to catalog payloads with orchestration pattern tags."""

from __future__ import annotations

from app.common.schemas.recipes_catalog import RecipeCatalogItem
from app.domain.recipes.orchestration_pattern_stacks import resolve_pattern_tags
from app.infrastructure.persistence.models.recipe import Recipe


def recipe_to_catalog_item(recipe: Recipe) -> RecipeCatalogItem:
    """Serialize one recipe with resolved agentic pattern stack metadata."""

    meta = resolve_pattern_tags(name=recipe.name, workflow_template=recipe.workflow_template)
    base = RecipeCatalogItem.model_validate(recipe)
    return base.model_copy(
        update={
            "orchestration_template": meta.orchestration_template,
            "pattern_tags": meta.pattern_tags,
            "pattern_labels": meta.pattern_labels,
        },
    )


__all__ = ["recipe_to_catalog_item"]
