#!/usr/bin/env python3
"""One-shot Chroma → Qdrant migration (legacy). Prefer ``migrate_vectors_to_pgvector.py`` for pgvector.

Run from repo root with both services reachable, for example::

    VECTOR_STORE_BACKEND=chroma CHROMA_HOST=localhost CHROMA_PORT=8001 \\
      QDRANT_HOST=localhost QDRANT_PORT=6333 \\
      python backend/scripts/migrate_chroma_to_qdrant.py

Requires ``chromadb`` and ``qdrant-client`` (already in backend requirements).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Allow ``python backend/scripts/...`` without installing the package.
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


COLLECTIONS = ("knowledge", "recipes", "agent_memories", "task_deliverables", "hive_mind")
_DOCUMENT_KEY = "_qs_document"
_VECTOR_SIZE = 384


def _migrate_collection(
    chroma_host: str,
    chroma_port: int,
    qdrant_host: str,
    qdrant_port: int,
    name: str,
    dry_run: bool,
) -> int:
    """Copy one Chroma collection into Qdrant; returns number of points written."""

    import chromadb
    from qdrant_client import QdrantClient
    from qdrant_client.http.exceptions import UnexpectedResponse
    from qdrant_client.models import Distance, PointStruct, VectorParams

    chroma = chromadb.HttpClient(host=chroma_host, port=chroma_port)
    coll = chroma.get_collection(name=name)
    raw = coll.get(include=["embeddings", "documents", "metadatas"])
    ids = raw.get("ids") or []
    embeddings = raw.get("embeddings")
    documents = raw.get("documents")
    metadatas = raw.get("metadatas")
    if not ids:
        print(f"[skip] {name}: empty")
        return 0

    client = QdrantClient(host=qdrant_host, port=qdrant_port)
    try:
        client.get_collection(collection_name=name)
    except UnexpectedResponse as exc:
        if getattr(exc, "status_code", None) != 404:
            raise
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
        )

    points: list[PointStruct] = []
    for idx, pid in enumerate(ids):
        emb = None
        if embeddings is not None and idx < len(embeddings):
            emb = embeddings[idx]
        if emb is None:
            print(f"[warn] {name}: id {pid} missing embedding — skipped")
            continue
        vec = list(emb)
        if len(vec) != _VECTOR_SIZE:
            print(f"[warn] {name}: id {pid} dim {len(vec)} != {_VECTOR_SIZE} — skipped")
            continue
        meta = dict(metadatas[idx]) if metadatas and idx < len(metadatas) and metadatas[idx] else {}
        doc = ""
        if documents and idx < len(documents) and documents[idx]:
            doc = str(documents[idx])
        payload = {**meta, _DOCUMENT_KEY: doc}
        points.append(PointStruct(id=str(pid), vector=vec, payload=payload))

    if dry_run:
        print(f"[dry-run] {name}: would upsert {len(points)} points")
        return len(points)

    batch = 64
    written = 0
    for i in range(0, len(points), batch):
        chunk = points[i : i + batch]
        client.upsert(collection_name=name, points=chunk)
        written += len(chunk)
    print(f"[ok] {name}: upserted {written} points")
    return written


def main() -> int:
    """CLI entry — environment overrides defaults."""

    parser = argparse.ArgumentParser(description="Migrate Chroma collections into Qdrant.")
    parser.add_argument("--dry-run", action="store_true", help="Count only, no writes.")
    parser.add_argument(
        "--collections",
        default=",".join(COLLECTIONS),
        help="Comma-separated Chroma collection names.",
    )
    args = parser.parse_args()

    chroma_host = os.environ.get("CHROMA_HOST", "localhost")
    chroma_port = int(os.environ.get("CHROMA_PORT", "8000"))
    qdrant_host = os.environ.get("QDRANT_HOST", "localhost")
    qdrant_port = int(os.environ.get("QDRANT_PORT", "6333"))

    total = 0
    for name in [c.strip() for c in args.collections.split(",") if c.strip()]:
        total += _migrate_collection(
            chroma_host,
            chroma_port,
            qdrant_host,
            qdrant_port,
            name,
            dry_run=args.dry_run,
        )
    print(f"Done. Total points: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
