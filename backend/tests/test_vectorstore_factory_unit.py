"""Vector backend factory wiring (pgvector default vs Chroma rollback)."""

from __future__ import annotations

import pytest

from app.infrastructure.vectorstore.chroma_backend import ChromaVectorBackend
from app.infrastructure.vectorstore.factory import get_vector_backend, reset_vector_backend_for_tests
from app.infrastructure.vectorstore.pgvector_backend import PgvectorVectorBackend


@pytest.mark.asyncio
async def test_factory_returns_pgvector_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit ``pgvector`` backend yields ``PgvectorVectorBackend``."""

    from app.core.config import settings

    monkeypatch.setattr(settings, "vector_store_backend", "pgvector", raising=False)
    reset_vector_backend_for_tests()
    backend = await get_vector_backend()
    assert isinstance(backend, PgvectorVectorBackend)


@pytest.mark.asyncio
async def test_factory_returns_chroma_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Operators may flip ``VECTOR_STORE_BACKEND=chroma`` during migration rollback."""

    from app.core.config import settings

    monkeypatch.setattr(settings, "vector_store_backend", "chroma", raising=False)
    reset_vector_backend_for_tests()
    backend = await get_vector_backend()
    assert isinstance(backend, ChromaVectorBackend)


@pytest.mark.asyncio
async def test_factory_returns_cached_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    """Second lookup reuses the same backend instance (fast path under lock)."""

    from app.core.config import settings

    monkeypatch.setattr(settings, "vector_store_backend", "pgvector", raising=False)
    reset_vector_backend_for_tests()
    first = await get_vector_backend()
    second = await get_vector_backend()
    assert first is second
