# Audit: ChromaDB, Neo4j, and pgvector (2026-05-14)

This document records **where** Chroma and Neo4j appear in the codebase and **why** the default vector tier is already **PostgreSQL + pgvector**, not a separate Chroma container.

## Postgres + pgvector (current default)

- Compose: `postgres` uses image **`pgvector/pgvector:pg16`** in `docker-compose.yml`, `docker-compose.base.yml`, and `docker-compose.stg.yml` (prod overlay extends base).
- Persistence: table **`hive_vector_documents`** and Alembic revision **`0016_pgvector_hive_vectors`** (see `backend/alembic/versions/`).
- Runtime: `VECTOR_STORE_BACKEND` defaults to **`pgvector`**; implementation is `PgvectorVectorBackend` (`backend/app/infrastructure/vectorstore/pgvector_backend.py`).
- Public API: features should use **`app.core.chroma_client`** (`embed_and_store`, `semantic_search`, …), which delegates to `get_vector_backend()` — the name is historical; behaviour is backend-selected.

## ChromaDB (soft / rollback only)

| Area | Role |
|------|------|
| `backend/app/infrastructure/vectorstore/chroma_backend.py` | HTTP Chroma client when `VECTOR_STORE_BACKEND=chroma`. |
| `backend/app/infrastructure/vectorstore/factory.py` | Selects `ChromaVectorBackend` vs `PgvectorVectorBackend`. |
| `backend/app/core/config.py` | `chroma_host`, `chroma_port`, `vector_store_backend`. |
| `backend/app/core/chroma_client.py` | Façade over vector backend (not a second schema). |

**Import strategy:** `chromadb` is imported **only** when the Chroma backend is actually constructed or when `_get_client()` runs (lazy), so default **pgvector** processes do not load the Chroma Python package at startup.

## Neo4j (still required for graph features)

| Area | Role |
|------|------|
| `backend/app/core/neo4j_client.py` | Async driver, knowledge nodes, links, decay, imitation edges. |
| `backend/app/core/readiness.py` | Optional hard gate via `readiness_require_neo4j`. |
| `backend/app/domain/hive_mind/graph.py` | Graph reads/writes and snapshots. |
| `backend/app/application/services/swarm_post_mortem.py` | Knowledge node creation + `record_imitation`. |
| `backend/app/main.py`, `backend/app/worker/pool_reset.py` | `close_neo4j` on shutdown / pool reset. |

Removing the **neo4j** package or the **Neo4j** service without replacing these call sites would break Hive Mind exports, post-mortem graph writes, and readiness when Neo4j is required. A future epic could add **Postgres JSONB + optional driver** with feature flags; that is **not** a drop-in shim.

## Requirements note

- **`chromadb`** remains in `requirements.txt` for operators who set `VECTOR_STORE_BACKEND=chroma` (migration / rollback).
- **`neo4j`** remains required for current graph code paths.

## Block checklist (operator request vs repo reality)

| Block | Status / note |
|-------|----------------|
| 1 Audit | This file + grep snapshots in repo CI / local. |
| 2 Enable pgvector | Already enabled via image + migrations; use `CREATE EXTENSION vector` if bootstrapping a raw DB. |
| 3 Alternate `hive_vectors` module | **Not adopted** — duplicates `hive_vector_documents` / `PgvectorVectorBackend`. |
| 4 Replace `chroma_client` with minimal shim | **Rejected** — would break `embed_and_store`, `find_similar_recipes`, collection constants, tests. |
| 5 Replace `neo4j_client` with PG-only shim | **Rejected** until graph domain is reimplemented in SQL. |
| 6–7 Strip deps / compose services | **Risky** without the reimplementation above; staging/prod still expect Neo4j for graph. |
| 8 Chroma → pgvector data copy | Use one-off script when Chroma is reachable and backend is temporarily `chroma`; default path is already pgvector. |
