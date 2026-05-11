"""Bee-hive FastAPI entrypoint tying PostgreSQL, ChromaDB, Neo4j, and Redis scaffolding."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.chroma_client import ensure_collections
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.logging import configure_logging
from app.core.neo4j_client import close_neo4j
from app.api.routers import workflows as workflows_router
from app.core.redis_client import close_redis


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Warm structured logging plus persistence clients before accepting traffic."""

    configure_logging(level="INFO")
    await init_db()
    await ensure_collections()
    yield
    await close_redis()
    await close_neo4j()
    await close_db()


app = FastAPI(
    title="Queenswarm Bee-Hive API",
    description="100+ autonomous agents · decentralized swarms · rapid reward learning",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app)

app.include_router(workflows_router.router, prefix="/api/v1/workflows")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin).strip() for origin in settings.cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Operational heartbeat for dashboards and swarm probes."""

    return {
        "status": "healthy",
        "service": "queenswarm-api",
        "version": "2.0.0",
        "domain": settings.domain,
    }


@app.get("/", response_class=PlainTextResponse)
async def hive_welcome() -> str:
    """Human-friendly swarm landing referencing the hive dashboard."""

    link = "https://" + settings.domain.strip()
    ascii_hive = r"""
Welcome to Queenswarm — Bee-Hive Cognitive OS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ⬡   decentralized scouts · evaluators · sims · actors
           Auto Workflow Breaker → LangGraph routing → Verified Output to humans
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
              Global Hive Sync ≤ 300s · Rapid Loop ≤ """ + str(
        settings.rapid_loop_timeout_sec
    )
    ascii_hive += """s · Pollen on proof
"""
    ascii_hive += f"""
Bee-Hive Dashboard: {link}

Only simulated, verified payloads cross the veil to operators — raw LLM dribble stays in-cell.
"""
    return ascii_hive.strip()
