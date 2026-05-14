"""Process-wide vector backend selection (pgvector default, Chroma rollback)."""

from __future__ import annotations

import asyncio
from typing import Literal

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.vectorstore.protocol import VectorStoreBackend

logger = get_logger(__name__)

_backend_lock = asyncio.Lock()
_backend: VectorStoreBackend | None = None


def _backend_kind() -> Literal["pgvector", "chroma"]:
    """Resolve configured backend with safe default."""

    raw = (settings.vector_store_backend or "pgvector").strip().lower()
    if raw == "chroma":
        return "chroma"
    return "pgvector"


async def get_vector_backend() -> VectorStoreBackend:
    """Return shared backend instance for the running process."""

    global _backend
    if _backend is not None:
        return _backend
    async with _backend_lock:
        if _backend is None:
            kind = _backend_kind()
            if kind == "chroma":
                from app.infrastructure.vectorstore.chroma_backend import ChromaVectorBackend

                _backend = ChromaVectorBackend()
                logger.info(
                    "vectorstore.backend_selected",
                    agent_id="vectorstore",
                    swarm_id="",
                    task_id="",
                    backend="chroma",
                )
            else:
                from app.infrastructure.vectorstore.pgvector_backend import PgvectorVectorBackend

                _backend = PgvectorVectorBackend()
                logger.info(
                    "vectorstore.backend_selected",
                    agent_id="vectorstore",
                    swarm_id="",
                    task_id="",
                    backend="pgvector",
                )
    assert _backend is not None
    return _backend


def reset_vector_backend_for_tests() -> None:
    """Clear singleton between pytest cases."""

    global _backend
    _backend = None
