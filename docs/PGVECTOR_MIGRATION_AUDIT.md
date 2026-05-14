# PGVECTOR migration — Block 1 audit (2026-05-14)

Canonical vector I/O remains `app.core.chroma_client` (`embed_and_store`, `semantic_search`, `delete_documents_by_ids`, `ping_vector_store`). Implementations live under `app.infrastructure.vectorstore/`.

## Chroma / `chroma_client` usage (grep)

```
backend/app/application/services/recipe_chroma_sync.py:from app.core.chroma_client import RECIPE_LIBRARY_COLLECTION, delete_documents_by_ids, embed_and_store
backend/app/application/services/recipe_chroma_bridge.py:from app.core.chroma_client import RECIPE_LIBRARY_COLLECTION, semantic_search
backend/app/core/config.py:    chroma_host: str = "chromadb"
backend/app/core/chroma_client.py:async def get_chroma_client() -> Any:
backend/app/core/readiness.py:from app.core.chroma_client import ping_vector_store
backend/app/domain/workflows/breaker.py:from app.core.chroma_client import find_similar_recipes
backend/app/domain/outputs/service.py:from app.core.chroma_client import TASK_DELIVERABLES_COLLECTION, embed_and_store
backend/app/domain/hive_mind/service.py:    embed_and_store,
backend/app/infrastructure/connectors/phase3/obsidian_sync.py:from app.core.chroma_client import HIVE_MIND_COLLECTION, embed_and_store
backend/app/infrastructure/vectorstore/factory.py:from app.infrastructure.vectorstore.chroma_backend import ChromaVectorBackend
backend/app/infrastructure/vectorstore/chroma_backend.py:import chromadb
backend/app/main.py:from app.core.chroma_client import ensure_collections
backend/app/presentation/api/routers/outputs.py:from app.core.chroma_client import TASK_DELIVERABLES_COLLECTION, semantic_search
backend/app/presentation/api/routers/hive_mind.py:from app.core.chroma_client import HIVE_MIND_COLLECTION, semantic_search
```

## Qdrant usage (grep, pre-removal)

```
backend/app/core/config.py:    vector_store_backend: Literal["qdrant", "chroma"] = Field(
backend/app/infrastructure/vectorstore/qdrant_backend.py:class QdrantVectorBackend:
backend/app/infrastructure/vectorstore/factory.py:from app.infrastructure.vectorstore.qdrant_backend import QdrantVectorBackend
```

## Collections / data shape

Hive collections (same names for all backends): `knowledge`, `recipes`, `agent_memories`, `task_deliverables`, `hive_mind` (see `chroma_client.py`). Embeddings: **384-d** MiniLM via `fastembed` (`embedder.py`), aligned with prior Qdrant collections.

## Neo4j (Block 7 preview)

`neo4j` is referenced from `readiness.py`, `swarm_post_mortem.py`, `hive_mind/service.py`, `neo4j_client.py`, and config. **Keep Neo4j** in Compose for this migration; do not remove based on vector work alone.
