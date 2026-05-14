"""Lazy-loaded local embeddings (MiniLM 384-d) aligned with legacy Chroma server defaults."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = get_logger(__name__)

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_embed_lock = asyncio.Lock()
_model: object | None = None


def _load_model() -> object:
    """Import and construct fastembed model (sync — call under lock or thread)."""

    from fastembed import TextEmbedding

    return TextEmbedding(model_name=_MODEL_NAME)


async def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Embed one or more strings using the shared MiniLM model (CPU, bounded RAM)."""

    global _model
    async with _embed_lock:
        if _model is None:
            _model = await asyncio.to_thread(_load_model)
            logger.info(
                "vectorstore.embedder_ready",
                agent_id="vectorstore",
                swarm_id="",
                task_id="",
                model=_MODEL_NAME,
            )
    model = _model

    def _run(batch: Sequence[str]) -> list[list[float]]:
        out: list[list[float]] = []
        gen = getattr(model, "embed")(list(batch))
        for row in gen:
            out.append(row.tolist())
        return out

    return await asyncio.to_thread(_run, texts)
