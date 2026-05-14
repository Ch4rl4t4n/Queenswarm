"""Vector recall façade — PostgreSQL + pgvector (default) or Chroma HTTP (rollback).

Public module name is historical; callers import ``embed_and_store`` / ``semantic_search`` unchanged.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.infrastructure.vectorstore.chroma_backend import get_chroma_async_client
from app.infrastructure.vectorstore.factory import get_vector_backend

_COLLECTION_KNOWLEDGE = "knowledge"
_COLLECTION_RECIPES = "recipes"
_COLLECTION_AGENT_MEMORIES = "agent_memories"
_COLLECTION_TASK_DELIVERABLES = "task_deliverables"
_COLLECTION_HIVE_MIND = "hive_mind"

RECIPE_LIBRARY_COLLECTION = _COLLECTION_RECIPES
TASK_DELIVERABLES_COLLECTION = _COLLECTION_TASK_DELIVERABLES
HIVE_MIND_COLLECTION = _COLLECTION_HIVE_MIND


class Recipe(BaseModel):
    """Verified workflow recipe resurfaced via Recipe Library cosine similarity."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    recipe_id: str
    document: str = ""
    workflow_steps: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    similarity: float = 0.0


def _recipe_steps_from_metadata(meta: dict[str, Any]) -> list[str]:
    """Extract ordered workflow steps persisted alongside recipe embeddings."""

    raw = meta.get("workflow_steps") or meta.get("steps")
    steps: list[str] = []
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if isinstance(raw, str):
        stripped = raw.strip()
        try:
            loaded = json.loads(stripped)
        except json.JSONDecodeError:
            return [stripped]
        else:
            if isinstance(loaded, list):
                return [str(item) for item in loaded]
            if isinstance(loaded, str):
                return [loaded]
    return steps


async def get_chroma_client() -> Any:
    """Return raw Chroma async client (only valid when ``VECTOR_STORE_BACKEND=chroma``)."""

    if settings.vector_store_backend != "chroma":
        raise RuntimeError(
            "get_chroma_client is only available when VECTOR_STORE_BACKEND=chroma; "
            "use delete_documents_by_ids / embed_and_store for portable vector IO.",
        )
    return await get_chroma_async_client()


async def embed_and_store(
    text: str,
    metadata: dict[str, Any],
    collection_name: str,
) -> str:
    """Embed ``text`` and persist metadata for swarm recall audits."""

    backend = await get_vector_backend()
    return await backend.embed_and_store(text, metadata, collection_name)


async def semantic_search(
    query: str,
    collection_name: str,
    n_results: int = 5,
) -> list[dict[str, Any]]:
    """Run vector retrieval and normalize rows for supervisor routing."""

    backend = await get_vector_backend()
    return await backend.semantic_search(query, collection_name, n_results=n_results)


async def delete_documents_by_ids(collection_name: str, ids: list[str]) -> None:
    """Delete embedding rows by id (Recipe Library mirrors, manual cleanups)."""

    backend = await get_vector_backend()
    await backend.delete_by_ids(collection_name, ids)


async def find_similar_recipes(
    task_text: str,
    threshold: float | None = None,
) -> Recipe | None:
    """Return the strongest verified recipe candidate above the cosine cutoff."""

    cutoff = (
        threshold if threshold is not None else settings.recipe_library_match_threshold
    )
    hits = await semantic_search(task_text, _COLLECTION_RECIPES, n_results=1)
    if not hits:
        return None
    top = hits[0]
    distance = top.get("distance")
    if distance is None:
        return None
    similarity = max(0.0, min(1.0, 1.0 - float(distance)))
    if similarity < cutoff:
        return None
    metadata = dict(top.get("metadata") or {})
    doc = top.get("document") or ""
    recipe_id = str(top.get("id") or "")
    steps = _recipe_steps_from_metadata(metadata)
    return Recipe(
        recipe_id=recipe_id,
        document=str(doc),
        workflow_steps=steps,
        metadata=metadata,
        similarity=float(similarity),
    )


async def ensure_collections() -> None:
    """Provision standard hive collections for knowledge, recipes, and bee memories."""

    backend = await get_vector_backend()
    await backend.ensure_collections()


async def ping_vector_store() -> None:
    """Connectivity probe for readiness (any backend)."""

    backend = await get_vector_backend()
    await backend.ping()
