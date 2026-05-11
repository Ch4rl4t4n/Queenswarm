"""Mutate Recipe Library rows and optionally mirror embeddings into Chroma."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.recipe import Recipe
from app.models.task import Task
from app.models.workflow import Workflow
from app.schemas.recipes_write import RecipeCreateBody, RecipePatchBody
from app.services.recipe_chroma_sync import (
    delete_recipe_embedding_from_chroma,
    upsert_recipe_into_chroma_library,
)

logger = get_logger(__name__)


class RecipeWriteConflictError(Exception):
    """Another recipe already owns the requested unique name."""


class RecipeWriteNotFoundError(Exception):
    """Primary key missing from the catalog."""


class RecipeWriteEmptyPatchError(Exception):
    """PATCH body omitted every mutable field."""


class RecipeWritePayloadTooLargeError(Exception):
    """workflow_template JSON exceeds configured byte budget."""

    def __init__(self, *, size_bytes: int, max_bytes: int) -> None:
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes
        super().__init__(f"workflow_template size {size_bytes} exceeds max {max_bytes}")


class RecipeWriteReferencedError(Exception):
    """Workflows or tasks still reference this recipe; refuse hard delete."""

    def __init__(self, *, reference_count: int) -> None:
        self.reference_count = reference_count
        super().__init__(f"recipe still referenced by {reference_count} row(s)")


def _ensure_workflow_template_size(data: dict[str, Any]) -> None:
    """Reject oversize templates to protect Postgres JSONB and outbound embedders."""

    raw = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    max_bytes = settings.recipe_workflow_template_max_json_bytes
    if len(raw) > max_bytes:
        raise RecipeWritePayloadTooLargeError(size_bytes=len(raw), max_bytes=max_bytes)


async def _recipe_reference_count(session: AsyncSession, recipe_id: uuid.UUID) -> int:
    """Count workflows/tasks still tied to this catalog row (FK-safe deletes)."""

    wf_stmt = select(func.count()).select_from(Workflow).where(Workflow.matching_recipe_id == recipe_id)
    tk_stmt = select(func.count()).select_from(Task).where(Task.recipe_used_id == recipe_id)
    wf = await session.scalar(wf_stmt)
    tk = await session.scalar(tk_stmt)
    return int(wf or 0) + int(tk or 0)


async def _name_taken(session: AsyncSession, name: str, *, exclude_id: uuid.UUID | None) -> bool:
    stmt = select(Recipe.id).where(Recipe.name == name.strip())
    if exclude_id is not None:
        stmt = stmt.where(Recipe.id != exclude_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _sync_embedding_best_effort(
    session: AsyncSession,
    recipe: Recipe,
    *,
    swarm_id: str = "",
    task_id: str = "",
) -> None:
    """Upsert Chroma row when enabled; swallow failures so Postgres stays authoritative."""

    if not settings.recipe_write_sync_chroma:
        return
    ctx = logger.bind(
        swarm_id=swarm_id,
        task_id=task_id,
        recipe_id=str(recipe.id),
    )
    try:
        recipe.embedding_id = await upsert_recipe_into_chroma_library(recipe)
        await session.flush()
    except Exception as exc:
        ctx.warning(
            "recipe_write.chroma_sync_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )


async def create_recipe_entry(
    session: AsyncSession,
    body: RecipeCreateBody,
    *,
    swarm_id: str = "",
    task_id: str = "",
) -> Recipe:
    """Insert a recipe row and optionally refresh its Recipe Library embedding."""

    if await _name_taken(session, body.name.strip(), exclude_id=None):
        raise RecipeWriteConflictError(body.name)

    _ensure_workflow_template_size(dict(body.workflow_template))

    verified_at: datetime | None = None
    if body.mark_verified:
        verified_at = datetime.now(tz=UTC)

    entity = Recipe(
        name=body.name.strip(),
        description=body.description,
        topic_tags=list(body.topic_tags or []),
        workflow_template=dict(body.workflow_template),
        success_count=0,
        fail_count=0,
        avg_pollen_earned=0.0,
        embedding_id=None,
        created_by_agent_id=body.created_by_agent_id,
        verified_at=verified_at,
        last_used_at=None,
        is_deprecated=False,
    )
    session.add(entity)
    await session.flush()

    await _sync_embedding_best_effort(
        session,
        entity,
        swarm_id=swarm_id,
        task_id=task_id,
    )

    ctx = logger.bind(
        swarm_id=swarm_id,
        task_id=task_id,
        recipe_id=str(entity.id),
    )
    ctx.info("recipe_write.created", name=entity.name)
    return entity


async def update_recipe_entry(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    body: RecipePatchBody,
    *,
    swarm_id: str = "",
    task_id: str = "",
) -> Recipe:
    """Apply a partial update and optionally re-embed."""

    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise RecipeWriteEmptyPatchError

    recipe = await session.get(Recipe, recipe_id)
    if recipe is None:
        raise RecipeWriteNotFoundError

    if "name" in patch and patch["name"] is not None:
        candidate = str(patch["name"]).strip()
        if await _name_taken(session, candidate, exclude_id=recipe_id):
            raise RecipeWriteConflictError(candidate)
        recipe.name = candidate

    if "description" in patch:
        recipe.description = patch["description"]

    if "topic_tags" in patch and patch["topic_tags"] is not None:
        recipe.topic_tags = list(patch["topic_tags"])

    if "workflow_template" in patch and patch["workflow_template"] is not None:
        tpl = dict(patch["workflow_template"])
        _ensure_workflow_template_size(tpl)
        recipe.workflow_template = tpl

    if "is_deprecated" in patch and patch["is_deprecated"] is not None:
        recipe.is_deprecated = bool(patch["is_deprecated"])

    if "mark_verified" in patch and patch["mark_verified"] is not None:
        if patch["mark_verified"]:
            recipe.verified_at = datetime.now(tz=UTC)
        else:
            recipe.verified_at = None

    await session.flush()

    await _sync_embedding_best_effort(
        session,
        recipe,
        swarm_id=swarm_id,
        task_id=task_id,
    )

    ctx = logger.bind(
        swarm_id=swarm_id,
        task_id=task_id,
        recipe_id=str(recipe.id),
    )
    ctx.info("recipe_write.updated", name=recipe.name)
    return recipe


async def delete_recipe_entry(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    *,
    swarm_id: str = "",
    task_id: str = "",
) -> tuple[uuid.UUID, str]:
    """Remove a catalog row after FK checks; strip Chroma embedding when known."""

    recipe = await session.get(Recipe, recipe_id)
    if recipe is None:
        raise RecipeWriteNotFoundError

    refs = await _recipe_reference_count(session, recipe_id)
    if refs > 0:
        raise RecipeWriteReferencedError(reference_count=refs)

    name = recipe.name
    embed_id = recipe.embedding_id
    await delete_recipe_embedding_from_chroma(embedding_id=embed_id)

    session.delete(recipe)
    await session.flush()

    ctx = logger.bind(
        swarm_id=swarm_id,
        task_id=task_id,
        recipe_id=str(recipe_id),
    )
    ctx.info("recipe_write.deleted", name=name)
    return recipe_id, name


__all__ = [
    "RecipeWriteConflictError",
    "RecipeWriteEmptyPatchError",
    "RecipeWriteNotFoundError",
    "RecipeWritePayloadTooLargeError",
    "RecipeWriteReferencedError",
    "create_recipe_entry",
    "delete_recipe_entry",
    "update_recipe_entry",
]
