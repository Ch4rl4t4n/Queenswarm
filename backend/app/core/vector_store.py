"""Queenswarm vector tier — PostgreSQL + pgvector (default) via the stable ``chroma_client`` façade.

Operators and features should import from ``app.core.chroma_client`` (``embed_and_store``,
``semantic_search``, ``delete_documents_by_ids``, ``ping_vector_store``). This module exists as a
single named entrypoint for documentation and optional ``from app.core.vector_store import …`` style imports.
"""

from __future__ import annotations

from app.core.chroma_client import (
    HIVE_MIND_COLLECTION,
    RECIPE_LIBRARY_COLLECTION,
    TASK_DELIVERABLES_COLLECTION,
    delete_documents_by_ids,
    embed_and_store,
    ensure_collections,
    find_similar_recipes,
    get_chroma_client,
    ping_vector_store,
    semantic_search,
)

__all__ = [
    "HIVE_MIND_COLLECTION",
    "RECIPE_LIBRARY_COLLECTION",
    "TASK_DELIVERABLES_COLLECTION",
    "delete_documents_by_ids",
    "embed_and_store",
    "ensure_collections",
    "find_similar_recipes",
    "get_chroma_client",
    "ping_vector_store",
    "semantic_search",
]
