"""Upsert verified Postgres recipes into Chroma Recipe Library embeddings."""

from __future__ import annotations

import json
from typing import Any

from app.core.chroma_client import RECIPE_LIBRARY_COLLECTION, embed_and_store, get_chroma_client
from app.core.logging import get_logger
from app.models.recipe import Recipe

logger = get_logger(__name__)


def _step_labels_from_template(template: dict[str, Any]) -> list[str]:
    """Pull human-readable labels from heterogeneous workflow templates."""

    steps_raw = template.get("steps") or template.get("workflow_steps") or []
    out: list[str] = []
    if isinstance(steps_raw, list):
        for item in steps_raw:
            if isinstance(item, dict):
                desc = item.get("description") or item.get("name") or item.get("title")
                out.append(str(desc or json.dumps(item, default=str)))
            else:
                out.append(str(item))
    elif isinstance(steps_raw, str) and steps_raw.strip():
        out.append(steps_raw.strip())
    return out


def recipe_embedding_document(recipe: Recipe) -> str:
    """Build a retrieval document string for cosine embedding."""

    tmpl = recipe.workflow_template or {}
    hints = ", ".join(_step_labels_from_template(tmpl))[:8000]
    parts: list[str] = [
        f"name: {recipe.name}",
        f"tags: {json.dumps(recipe.topic_tags or [], default=str)}",
        f"description: {recipe.description or ''}".strip(),
    ]
    if hints:
        parts.append(f"steps: {hints}")
    parts.append(f"workflow_template_json: {json.dumps(tmpl, default=str)}")
    return "\n".join(parts)


async def upsert_recipe_into_chroma_library(recipe: Recipe) -> str:
    """Delete the prior Chroma row (if any) and insert a fresh recipe embedding.

    Args:
        recipe: ORM row with ``workflow_template`` and optional ``embedding_id``.

    Returns:
        New Chroma document id stored in ``recipe.embedding_id`` by the caller.
    """

    ctx = logger.bind(recipe_id=str(recipe.id), agent_id=None, swarm_id="", task_id="")
    text = recipe_embedding_document(recipe)
    steps = _step_labels_from_template(recipe.workflow_template or {})
    metadata: dict[str, Any] = {
        "postgres_recipe_id": str(recipe.id),
        "recipe_name": recipe.name,
        "verified": bool(recipe.verified_at is not None),
        "workflow_steps": json.dumps(steps, default=str),
        "topic_tags": json.dumps(recipe.topic_tags or [], default=str),
    }

    prior = recipe.embedding_id
    if prior:
        try:
            client = await get_chroma_client()
            collection = await client.get_collection(name=RECIPE_LIBRARY_COLLECTION)
            await collection.delete(ids=[prior])
        except Exception as exc:
            ctx.warning(
                "recipe_chroma.prior_embedding_delete_failed",
                error_type=type(exc).__name__,
                error=str(exc),
                prior_embedding_id=str(prior)[:120],
            )

    doc_id = await embed_and_store(
        text,
        metadata,
        RECIPE_LIBRARY_COLLECTION,
    )
    ctx.info("recipe_chroma.embedding_upserted", embedding_id=str(doc_id)[:120])
    return doc_id


async def delete_recipe_embedding_from_chroma(*, embedding_id: str | None) -> None:
    """Remove a Recipe Library Chroma vector when the Postgres row is deleted.

    Best-effort: Chroma outages must not block catalog deletes (Postgres is source of truth).
    """

    if not embedding_id or not str(embedding_id).strip():
        return

    cleaned = str(embedding_id).strip()
    ctx = logger.bind(recipe_embedding_id=cleaned[:120], agent_id=None, swarm_id="", task_id="")
    try:
        client = await get_chroma_client()
        collection = await client.get_collection(name=RECIPE_LIBRARY_COLLECTION)
        await collection.delete(ids=[cleaned])
    except Exception as exc:
        ctx.warning(
            "recipe_chroma.embedding_delete_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return

    ctx.info("recipe_chroma.embedding_deleted")


__all__ = [
    "delete_recipe_embedding_from_chroma",
    "recipe_embedding_document",
    "upsert_recipe_into_chroma_library",
]
