#!/usr/bin/env python3
"""One-shot migration: Qdrant and/or Chroma collections → ``hive_vector_documents`` (pgvector).

Run from repo root (or inside the backend container) after ``alembic upgrade head``::

    VECTOR_STORE_BACKEND=pgvector \\
    QDRANT_HOST=qdrant QDRANT_PORT=6333 \\
    CHROMA_HOST=chromadb CHROMA_PORT=8000 \\
    python backend/scripts/migrate_vectors_to_pgvector.py --from-qdrant --from-chroma

``--dry-run`` counts rows only. Requires ``qdrant-client`` and/or ``chromadb`` when those flags are set.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

_DOCUMENT_KEY = "_qs_document"
_VECTOR_SIZE = 384


def _vec_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{float(v):.8f}" for v in values) + "]"


async def _insert_row(
    session: AsyncSession,
    *,
    doc_id: str,
    collection_name: str,
    document: str,
    metadata: dict[str, Any],
    embedding: list[float],
    dry_run: bool,
) -> None:
    if len(embedding) != _VECTOR_SIZE:
        raise ValueError(f"embedding dim {len(embedding)} != {_VECTOR_SIZE}")
    if dry_run:
        return
    await session.execute(
        text(
            """
            INSERT INTO hive_vector_documents
                (id, collection_name, document, metadata, embedding)
            VALUES
                (:id, :collection_name, :document, CAST(:metadata AS jsonb), CAST(:embedding AS vector))
            ON CONFLICT (id) DO NOTHING
            """,
        ),
        {
            "id": doc_id,
            "collection_name": collection_name,
            "document": document,
            "metadata": json.dumps(metadata),
            "embedding": _vec_literal(embedding),
        },
    )


async def migrate_from_qdrant(*, dry_run: bool) -> int:
    """Scroll Qdrant collections and upsert rows."""

    from qdrant_client import QdrantClient

    host = os.environ.get("QDRANT_HOST", "localhost")
    port = int(os.environ.get("QDRANT_PORT", "6333"))
    client = QdrantClient(host=host, port=port)
    from app.core.database import async_session

    migrated = 0
    async with async_session() as session:
        for col in client.get_collections().collections:
            name = col.name
            offset = None
            while True:
                points, offset = client.scroll(
                    collection_name=name,
                    limit=64,
                    offset=offset,
                    with_vectors=True,
                    with_payload=True,
                )
                if not points:
                    break
                for p in points:
                    payload = dict(p.payload or {})
                    doc = str(payload.pop(_DOCUMENT_KEY, None) or "")
                    vec = p.vector
                    if vec is None:
                        continue
                    emb = [float(x) for x in vec]
                    if len(emb) != _VECTOR_SIZE:
                        continue
                    pid = str(p.id) if p.id is not None else str(uuid.uuid4())
                    await _insert_row(
                        session,
                        doc_id=pid,
                        collection_name=name,
                        document=doc,
                        metadata=payload,
                        embedding=emb,
                        dry_run=dry_run,
                    )
                    migrated += 1
                if offset is None:
                    break
        if not dry_run:
            await session.commit()
    return migrated


async def migrate_from_chroma(*, dry_run: bool) -> int:
    """Read Chroma HTTP collections; re-embed when vectors are missing."""

    import chromadb

    host = os.environ.get("CHROMA_HOST", "chromadb")
    port = int(os.environ.get("CHROMA_PORT", "8000"))
    chroma = chromadb.HttpClient(host=host, port=port)
    from app.core.database import async_session
    from app.infrastructure.vectorstore.embedder import embed_texts
    from app.infrastructure.vectorstore.metadata import flatten_vector_metadata

    migrated = 0
    async with async_session() as session:
        for col in chroma.list_collections():
            name = col.name
            coll = chroma.get_collection(name=name)
            raw = coll.get(include=["embeddings", "documents", "metadatas"])
            ids = raw.get("ids") or []
            embeddings = raw.get("embeddings")
            documents = raw.get("documents")
            metadatas = raw.get("metadatas")
            if not ids:
                continue
            for idx, pid in enumerate(ids):
                doc = documents[idx] if documents and idx < len(documents) else ""
                if not doc:
                    continue
                meta = dict(metadatas[idx]) if metadatas and idx < len(metadatas) and metadatas[idx] else {}
                flat = flatten_vector_metadata(meta)
                emb_row = None
                if embeddings is not None and idx < len(embeddings):
                    emb_row = embeddings[idx]
                if emb_row is None:
                    emb = (await embed_texts([str(doc)]))[0]
                else:
                    emb = [float(x) for x in emb_row]
                if len(emb) != _VECTOR_SIZE:
                    continue
                payload = {**flat, _DOCUMENT_KEY: str(doc)}
                await _insert_row(
                    session,
                    doc_id=str(pid),
                    collection_name=name,
                    document=str(doc),
                    metadata=payload,
                    embedding=emb,
                    dry_run=dry_run,
                )
                migrated += 1
        if not dry_run:
            await session.commit()
    return migrated


async def _amain() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy vectors into hive_vector_documents.")
    parser.add_argument("--from-qdrant", action="store_true", help="Pull points from Qdrant.")
    parser.add_argument("--from-chroma", action="store_true", help="Pull rows from Chroma HTTP.")
    parser.add_argument("--dry-run", action="store_true", help="Count only; do not write.")
    args = parser.parse_args()
    if not args.from_qdrant and not args.from_chroma:
        parser.error("Specify at least one of --from-qdrant or --from-chroma")
    total = 0
    if args.from_qdrant:
        n = await migrate_from_qdrant(dry_run=args.dry_run)
        print(f"Qdrant candidates processed: {n}")
        total += n
    if args.from_chroma:
        n = await migrate_from_chroma(dry_run=args.dry_run)
        print(f"Chroma rows processed: {n}")
        total += n
    print(f"Total: {total} ({'dry-run' if args.dry_run else 'written'})")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
