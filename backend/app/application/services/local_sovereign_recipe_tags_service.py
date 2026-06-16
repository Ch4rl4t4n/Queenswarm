"""Track M LOC14 — ``local-adapter`` recipe tags + sovereign imitation hints."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.llm_routing import load_routing_config
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.recipe import Recipe

_logger = get_logger(__name__)

LOCAL_ADAPTER_TOPIC_TAG = "local-adapter"


class SovereignRecipeHintOut(BaseModel):
    """One recipe recommended for local sovereign imitation."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: str
    name: str
    topic_tags: list[str] = Field(default_factory=list)
    success_rate: float = 0.0
    imitation_hint: str = ""


class SovereignImitationHintsSnapshotOut(BaseModel):
    """Operator snapshot for sovereign recipe imitation lane."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    sovereign_mode: bool
    imitation_boost: float = 0.0
    local_adapter_recipe_count: int = 0
    hints: list[SovereignRecipeHintOut] = Field(default_factory=list)
    operator_hint: str = ""


def ensure_local_adapter_topic_tag(tags: list[str] | None) -> list[str]:
    """Return topic tags with ``local-adapter`` present exactly once (case-insensitive)."""

    normalized = [str(t).strip() for t in (tags or []) if str(t).strip()]
    lowered = {t.lower() for t in normalized}
    if LOCAL_ADAPTER_TOPIC_TAG not in lowered:
        normalized.append(LOCAL_ADAPTER_TOPIC_TAG)
    return normalized


def recipe_has_local_adapter_tag(recipe: Recipe | None) -> bool:
    """Return True when recipe carries the sovereign ``local-adapter`` topic tag."""

    if recipe is None:
        return False
    tags = recipe.topic_tags if isinstance(recipe.topic_tags, list) else []
    return LOCAL_ADAPTER_TOPIC_TAG in {str(t).strip().lower() for t in tags if str(t).strip()}


def sovereign_recipe_similarity_boost(*, recipe: Recipe | None, sovereign_mode: bool) -> float:
    """Extra hybrid-score boost for ``local-adapter`` recipes in sovereign routing."""

    if not sovereign_mode or not settings.local_sovereign_recipe_tags_enabled:
        return 0.0
    if not recipe_has_local_adapter_tag(recipe):
        return 0.0
    return float(settings.local_sovereign_recipe_imitation_boost)


async def tenant_uses_local_sovereign(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> bool:
    """Return True when tenant routing is air-gap or ``local_sovereign``."""

    if settings.llm_airgap:
        return True
    cfg = await load_routing_config(session, tenant_id=tenant_id)
    return str(cfg.get("routing_mode") or "") == "local_sovereign"


async def apply_local_adapter_tag_to_recipe(
    session: AsyncSession,
    *,
    recipe_id: uuid.UUID,
) -> Recipe | None:
    """Persist ``local-adapter`` on one recipe topic tag list."""

    if not settings.local_sovereign_recipe_tags_enabled:
        return None
    recipe = await session.get(Recipe, recipe_id)
    if recipe is None:
        return None
    recipe.topic_tags = ensure_local_adapter_topic_tag(
        list(recipe.topic_tags) if isinstance(recipe.topic_tags, list) else [],
    )
    await session.commit()
    await session.refresh(recipe)
    _logger.info(
        "local_sovereign_recipe_tags.tagged",
        recipe_id=str(recipe_id),
        tag=LOCAL_ADAPTER_TOPIC_TAG,
    )
    return recipe


async def apply_local_adapter_tags_to_recipes(
    session: AsyncSession,
    *,
    recipe_ids: list[uuid.UUID],
) -> int:
    """Tag multiple recipes; returns count updated."""

    updated = 0
    for rid in recipe_ids:
        row = await apply_local_adapter_tag_to_recipe(session, recipe_id=rid)
        if row is not None:
            updated += 1
    return updated


async def list_local_adapter_tagged_recipes(
    session: AsyncSession,
    *,
    limit: int = 12,
) -> list[Recipe]:
    """Return verified recipes tagged ``local-adapter``, best success rate first."""

    cap = min(max(limit, 1), 50)
    stmt = (
        select(Recipe)
        .where(Recipe.is_deprecated.is_(False))
        .where(Recipe.topic_tags.contains([LOCAL_ADAPTER_TOPIC_TAG]))
        .order_by(Recipe.success_count.desc(), Recipe.updated_at.desc())
        .limit(cap)
    )
    rows = list((await session.scalars(stmt)).all())
    return rows


async def compose_sovereign_imitation_hints_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> SovereignImitationHintsSnapshotOut:
    """Build LOC14 imitation hints for Settings / recipe search boost context."""

    enabled = settings.local_llm_enabled and settings.local_sovereign_recipe_tags_enabled
    sovereign = await tenant_uses_local_sovereign(session, tenant_id=tenant_id) if enabled else False
    if not enabled:
        return SovereignImitationHintsSnapshotOut(
            enabled=False,
            sovereign_mode=False,
            operator_hint="Enable LOCAL_LLM_ENABLED and local sovereign recipe tags.",
        )

    rows = await list_local_adapter_tagged_recipes(session, limit=8)
    hints: list[SovereignRecipeHintOut] = []
    for recipe in rows:
        hints.append(
            SovereignRecipeHintOut(
                recipe_id=str(recipe.id),
                name=recipe.name,
                topic_tags=list(recipe.topic_tags or [])[:8],
                success_rate=float(recipe.success_rate),
                imitation_hint=(
                    "Proven on local adapter — prefer for sovereign session routines."
                    if sovereign
                    else "Tagged for local adapter reuse when routing is local_sovereign."
                ),
            ),
        )

    return SovereignImitationHintsSnapshotOut(
        enabled=True,
        sovereign_mode=sovereign,
        imitation_boost=float(settings.local_sovereign_recipe_imitation_boost),
        local_adapter_recipe_count=len(rows),
        hints=hints,
        operator_hint=(
            "Link recipes when registering adapters — semantic search boosts local-adapter tags in sovereign mode."
            if sovereign
            else "Switch routing to local_sovereign to activate imitation boost on tagged recipes."
        ),
    )


__all__ = [
    "LOCAL_ADAPTER_TOPIC_TAG",
    "SovereignImitationHintsSnapshotOut",
    "SovereignRecipeHintOut",
    "apply_local_adapter_tag_to_recipe",
    "apply_local_adapter_tags_to_recipes",
    "compose_sovereign_imitation_hints_snapshot",
    "ensure_local_adapter_topic_tag",
    "list_local_adapter_tagged_recipes",
    "recipe_has_local_adapter_tag",
    "sovereign_recipe_similarity_boost",
    "tenant_uses_local_sovereign",
]
