"""Async Chroma HTTP client hooks for swarm memories and Recipe Library cosine recall."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import chromadb
from chromadb.api.async_api import AsyncClientAPI
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings

_COLLECTION_KNOWLEDGE = "knowledge"
_COLLECTION_RECIPES = "recipes"
_COLLECTION_AGENT_MEMORIES = "agent_memories"

# Public alias matching ``_COLLECTION_RECIPES`` for routers and services outside this module.
RECIPE_LIBRARY_COLLECTION = _COLLECTION_RECIPES

_chroma_lock = asyncio.Lock()
_chroma_client: AsyncClientAPI | None = None


class Recipe(BaseModel):
    """Verified workflow recipe resurfaced via Recipe Library cosine similarity."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    recipe_id: str
    document: str = ""
    workflow_steps: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    similarity: float = 0.0


def _flatten_chroma_metadata(
    metadata: dict[str, Any] | None,
) -> dict[str, str | int | float | bool]:
    """Normalize arbitrary metadata dict into Chroma-legal scalar payloads."""

    if not metadata:
        return {}
    safe: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            safe[str(key)] = value
        else:
            safe[str(key)] = json.dumps(value, default=str)
    return safe


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


async def get_chroma_client() -> AsyncClientAPI:
    """Yield a warmed Async HTTP client targeting the hive Chroma daemon."""

    global _chroma_client
    async with _chroma_lock:
        if _chroma_client is None:
            _chroma_client = await chromadb.AsyncHttpClient(
                host=settings.chroma_host,
                port=int(settings.chroma_port),
                ssl=False,
            )
    assert _chroma_client is not None
    return _chroma_client


async def embed_and_store(
    text: str,
    metadata: dict[str, Any],
    collection_name: str,
) -> str:
    """Embed ``text`` on the cluster and persist metadata for swarm recall audits.

    Returns:
        Stable document identifier suitable for lineage tracking.
    """

    client = await get_chroma_client()
    collection = await client.get_collection(name=collection_name)
    doc_id = str(uuid.uuid4())
    normalized = _flatten_chroma_metadata(metadata)
    await collection.add(ids=[doc_id], documents=[text], metadatas=[normalized])
    return doc_id


async def semantic_search(
    query: str,
    collection_name: str,
    n_results: int = 5,
) -> list[dict[str, Any]]:
    """Run async vector retrieval and normalize rows for supervisor routing."""

    client = await get_chroma_client()
    collection = await client.get_collection(name=collection_name)
    raw = await collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    flattened: list[dict[str, Any]] = []
    ids_batch = raw.get("ids")
    distances_batch = raw.get("distances")
    documents_batch = raw.get("documents")
    metadata_batch = raw.get("metadatas")
    if not ids_batch or not ids_batch[0]:
        return flattened
    for idx in range(len(ids_batch[0])):
        doc_id = ids_batch[0][idx]
        doc_value = None
        if documents_batch and documents_batch[0] and idx < len(documents_batch[0]):
            doc_value = documents_batch[0][idx]
        distance = None
        if distances_batch and distances_batch[0] and idx < len(distances_batch[0]):
            distance = distances_batch[0][idx]
        metadata_row: dict[str, Any] = {}
        if metadata_batch and metadata_batch[0] and idx < len(metadata_batch[0]):
            blob = metadata_batch[0][idx]
            if isinstance(blob, dict):
                metadata_row = blob
        flattened.append(
            {
                "id": doc_id,
                "document": doc_value,
                "metadata": metadata_row,
                "distance": distance,
            },
        )
    return flattened


async def find_similar_recipes(
    task_text: str,
    threshold: float | None = None,
) -> Recipe | None:
    """Return the strongest verified recipe candidate above the cosine cutoff.

    Chroma cosine ``distance`` is translated to ``similarity = 1 - distance`` assuming
    the server uses cosine space for the Recipe Library collection (hive default).

    Args:
        task_text: User or breaker task narration used as the retrieval query.
        threshold: Explicit cutoff; defaults to ``settings.recipe_library_match_threshold``.
    """

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

    client = await get_chroma_client()
    for collection in (
        _COLLECTION_KNOWLEDGE,
        _COLLECTION_RECIPES,
        _COLLECTION_AGENT_MEMORIES,
    ):
        await client.get_or_create_collection(name=collection)
