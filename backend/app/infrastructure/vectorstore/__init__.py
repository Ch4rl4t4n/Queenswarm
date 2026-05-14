"""Pluggable vector persistence (pgvector primary, Chroma legacy)."""

from __future__ import annotations

from app.infrastructure.vectorstore.factory import get_vector_backend, reset_vector_backend_for_tests
from app.infrastructure.vectorstore.protocol import VectorStoreBackend

__all__ = [
    "VectorStoreBackend",
    "get_vector_backend",
    "reset_vector_backend_for_tests",
]
