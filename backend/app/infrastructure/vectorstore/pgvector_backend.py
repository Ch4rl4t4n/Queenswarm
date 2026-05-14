"""PostgreSQL + pgvector backend — same collections as legacy Chroma/Qdrant (384-d MiniLM)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import text

from app.core.database import async_session
from app.core.logging import get_logger
from app.infrastructure.vectorstore.embedder import embed_texts
from app.infrastructure.vectorstore.metadata import flatten_vector_metadata

logger = get_logger(__name__)

_VECTOR_SIZE = 384
_DOCUMENT_PAYLOAD_KEY = "_qs_document"
_DEFAULT_COLLECTIONS = (
    "knowledge",
    "recipes",
    "agent_memories",
    "task_deliverables",
    "hive_mind",
)


def _vector_literal(values: list[float]) -> str:
    """Format a float list for PostgreSQL ``vector`` casts."""

    return "[" + ",".join(f"{float(v):.8f}" for v in values) + "]"


class PgvectorVectorBackend:
    """Async SQLAlchemy + pgvector implementation of ``VectorStoreBackend``."""

    async def ensure_collections(self) -> None:
        """No per-collection remote provisioning — table is shared; verify table exists."""

        async with async_session() as session:
            res = await session.execute(
                text(
                    "SELECT to_regclass('public.hive_vector_documents') IS NOT NULL AS ok",
                ),
            )
            row = res.fetchone()
            if not row or not row[0]:
                raise RuntimeError(
                    "hive_vector_documents missing — run ``alembic upgrade head`` on PostgreSQL with pgvector.",
                )
            await session.commit()

    async def embed_and_store(
        self,
        text_value: str,
        metadata: dict[str, Any],
        collection_name: str,
    ) -> str:
        """Embed locally, insert row with flattened metadata + document text."""

        vectors = await embed_texts([text_value])
        if not vectors or len(vectors[0]) != _VECTOR_SIZE:
            raise RuntimeError("Embedding pipeline returned no vectors or wrong dimension.")
        doc_id = str(uuid.uuid4())
        flat = flatten_vector_metadata(metadata)
        payload = {**flat, _DOCUMENT_PAYLOAD_KEY: text_value}
        emb_lit = _vector_literal(vectors[0])
        meta_json = json.dumps(payload)
        async with async_session() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO hive_vector_documents
                        (id, collection_name, document, metadata, embedding)
                    VALUES
                        (:id, :collection_name, :document, CAST(:metadata AS jsonb), CAST(:embedding AS vector))
                    """,
                ),
                {
                    "id": doc_id,
                    "collection_name": collection_name,
                    "document": text_value,
                    "metadata": meta_json,
                    "embedding": emb_lit,
                },
            )
            await session.commit()
        return doc_id

    async def semantic_search(
        self,
        query: str,
        collection_name: str,
        *,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Cosine distance via ``<=>``; expose Chroma-like ``distance`` (lower = closer)."""

        qvec = await embed_texts([query])
        if not qvec or len(qvec[0]) != _VECTOR_SIZE:
            return []
        emb_lit = _vector_literal(qvec[0])
        lim = max(1, int(n_results))
        async with async_session() as session:
            result = await session.execute(
                text(
                    """
                    SELECT
                        id,
                        document,
                        metadata,
                        (embedding <=> CAST(:qvec AS vector)) AS distance
                    FROM hive_vector_documents
                    WHERE collection_name = :collection_name
                    ORDER BY distance
                    LIMIT :lim
                    """,
                ),
                {
                    "qvec": emb_lit,
                    "collection_name": collection_name,
                    "lim": lim,
                },
            )
            rows = result.fetchall()
            await session.commit()
        out: list[dict[str, Any]] = []
        for row in rows:
            meta_raw = row[2]
            meta: dict[str, Any] = dict(meta_raw) if isinstance(meta_raw, dict) else {}
            dist = row[3]
            distance = float(dist) if dist is not None else None
            out.append(
                {
                    "id": str(row[0]),
                    "document": row[1],
                    "metadata": meta,
                    "distance": distance,
                },
            )
        return out

    async def delete_by_ids(self, collection_name: str, ids: list[str]) -> None:
        """Delete rows for this collection and id list."""

        if not ids:
            return
        async with async_session() as session:
            for raw_id in ids:
                await session.execute(
                    text(
                        """
                        DELETE FROM hive_vector_documents
                        WHERE collection_name = :collection_name AND id = :id
                        """,
                    ),
                    {"collection_name": collection_name, "id": str(raw_id)},
                )
            await session.commit()

    async def ping(self) -> None:
        """Require pgvector extension + hive table."""

        async with async_session() as session:
            ext = await session.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector' LIMIT 1"),
            )
            if ext.fetchone() is None:
                raise RuntimeError("pgvector extension is not installed on this database.")
            tbl = await session.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'hive_vector_documents' LIMIT 1",
                ),
            )
            if tbl.fetchone() is None:
                raise RuntimeError("hive_vector_documents table is missing.")
            await session.commit()
