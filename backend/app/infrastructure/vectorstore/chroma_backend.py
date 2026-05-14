"""Chroma HTTP vector backend (legacy rollback / migration source)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import chromadb
from chromadb.api.async_api import AsyncClientAPI

from app.core.config import settings
from app.infrastructure.vectorstore.metadata import flatten_vector_metadata

_COLLECTION_KNOWLEDGE = "knowledge"
_COLLECTION_RECIPES = "recipes"
_COLLECTION_AGENT_MEMORIES = "agent_memories"
_COLLECTION_TASK_DELIVERABLES = "task_deliverables"
_COLLECTION_HIVE_MIND = "hive_mind"

_chroma_lock = asyncio.Lock()
_chroma_client: AsyncClientAPI | None = None


async def _get_client() -> AsyncClientAPI:
    """Yield a warmed Async HTTP client targeting the Chroma daemon."""

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


class ChromaVectorBackend:
    """Async Chroma HTTP implementation of ``VectorStoreBackend``."""

    async def ensure_collections(self) -> None:
        """Provision standard hive collections."""

        client = await _get_client()
        for name in (
            _COLLECTION_KNOWLEDGE,
            _COLLECTION_RECIPES,
            _COLLECTION_AGENT_MEMORIES,
            _COLLECTION_TASK_DELIVERABLES,
            _COLLECTION_HIVE_MIND,
        ):
            await client.get_or_create_collection(name=name)

    async def embed_and_store(
        self,
        text: str,
        metadata: dict[str, Any],
        collection_name: str,
    ) -> str:
        """Embed server-side and persist metadata."""

        client = await _get_client()
        collection = await client.get_collection(name=collection_name)
        doc_id = str(uuid.uuid4())
        normalized = flatten_vector_metadata(metadata)
        await collection.add(ids=[doc_id], documents=[text], metadatas=[normalized])
        return doc_id

    async def semantic_search(
        self,
        query: str,
        collection_name: str,
        *,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Chroma cosine query with normalized rows."""

        client = await _get_client()
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

    async def delete_by_ids(self, collection_name: str, ids: list[str]) -> None:
        """Delete by Chroma row ids."""

        if not ids:
            return
        client = await _get_client()
        collection = await client.get_collection(name=collection_name)
        await collection.delete(ids=ids)

    async def ping(self) -> None:
        """Heartbeat or list collections."""

        client = await _get_client()
        heartbeat = getattr(client, "heartbeat", None)
        if callable(heartbeat):
            await heartbeat()
        else:
            await client.list_collections()


async def get_chroma_async_client() -> AsyncClientAPI:
    """Public hook for code paths that still need the raw Chroma client (legacy / tests)."""

    return await _get_client()
