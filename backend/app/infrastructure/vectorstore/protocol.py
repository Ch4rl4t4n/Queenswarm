"""Vector store backend contract — pgvector (default) or Chroma (legacy rollback)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class VectorStoreBackend(Protocol):
    """Async embeddings + cosine-style retrieval shared by HiveMind, recipes, outputs."""

    async def ensure_collections(self) -> None:
        """Provision standard hive collections if missing."""

    async def embed_and_store(
        self,
        text: str,
        metadata: dict[str, Any],
        collection_name: str,
    ) -> str:
        """Persist one vector row; returns stable point / document id."""

    async def semantic_search(
        self,
        query: str,
        collection_name: str,
        *,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Return normalized hits: id, document, metadata, distance (lower = closer for Chroma parity)."""

    async def delete_by_ids(self, collection_name: str, ids: list[str]) -> None:
        """Remove vectors by id (best-effort for catalog mirrors)."""

    async def ping(self) -> None:
        """Lightweight connectivity probe for readiness checks."""
