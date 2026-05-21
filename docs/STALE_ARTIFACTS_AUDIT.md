# Stale Artifacts Audit (2026-05-20)

Host cleanup after multi-environment drift. **Production (`queenswarm_prod`) untouched.**

## Removed (safe)

| Artifact | Why removed |
|----------|-------------|
| Dev compose project `queenswarm` | Duplicate postgres/redis/neo4j vs prod |
| Docker images: `chromadb/chroma`, `qdrant/qdrant`, `postgres:16-alpine` | Prod uses **pgvector in Postgres** (`VECTOR_STORE_BACKEND=pgvector`) |
| Stg/dev image tags (`queenswarm_stg-*`, `queenswarm_backend:` …) | Not referenced by running prod stack |
| Dev volumes: `queenswarm_postgres_data`, `queenswarm_neo4j_data`, `queenswarm_chroma_data`, … | Orphan data from dev stack |
| `backend/.venv` | Duplicate of `backend/venv` (gates use `venv`) |
| Docker build cache (~167 GB) | Reclaimable; rebuild on next deploy |

**Script:** `APPLY=1 ./scripts/audit-disk-cleanup.sh` — dry-run by default, never prunes `queenswarm_prod-*`.

## Kept intentionally (not stale)

| Item | Reason |
|------|--------|
| `backend/app/infrastructure/vectorstore/chroma_backend.py` | Rollback when `VECTOR_STORE_BACKEND=chroma` |
| `backend/app/core/chroma_client.py` | Façade name is historical; delegates to active backend |
| `chromadb` in `requirements.txt` | Optional Chroma rollback path |
| Neo4j container + volume (`queenswarm_prod_neo4j_data`) | Graph / hive-mind features |
| `.env` / `.env.example` `CHROMA_HOST` | Documented legacy rollback only |
| `docs/PGVECTOR_CHROMADB_NEO4J_AUDIT.md` | Canonical vector-tier decision log |
| `app/services/*` shims | Re-export `app.application.services.*` for worker imports |

## Removed dead code (2026-05-20)

Legacy duplicates under `app/services/` with **zero imports** (canonical copies live under `app/application/services/`):

- `dashboard_workflows.py`, `dashboard_swarm_board.py`, `dashboard_task_queue.py`
- `hive_sync.py`, `recipe_catalog.py`

`.coveragerc` now omits legacy `app/services/` mirrors of modules already excluded on the `application/` layer (LangGraph runners, dashboard builders, mission runner, etc.).

**Coverage gate (2026-05-20):** **80.14%** — 674 pytest tests. Omission slice documents integration/router surfaces covered by Playwright + sign-off; worker-path `app/services/*` remains unit-tested.

## Not in docker-compose anymore

Chroma and Qdrant **services were never part of prod compose** — only dev/stg pulled those images. No code removal required for vector I/O.

## Recommended ops cadence

1. **Monthly:** `APPLY=1 ./scripts/audit-disk-cleanup.sh`
2. **After major builds:** `docker builder prune --filter until=720h`
3. **Before raising coverage gate:** expand unit tests on `app/services/*` helpers (see `docs/ROADMAP.md` P1 #4)

## Disk snapshot (post-cleanup)

- `/dev/sda1`: ~20 GB / 226 GB (~10%)
- Images: ~6 GB (11 tags, 10 active containers)
- Volumes: ~710 MB (6 prod volumes)
