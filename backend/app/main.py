"""Bee-hive FastAPI entrypoint tying PostgreSQL, ChromaDB, Neo4j, and Redis scaffolding."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.middleware.rate_limit import RateLimitMiddleware
from app.api.routers import health as health_router
from app.api.v1 import api_v1
from app.core.chroma_client import ensure_collections
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.logging import configure_logging
from app.core.neo4j_client import close_neo4j
from app.core.redis_client import close_redis
from app.services.hive_waggle_relay import run_hive_waggle_relay_loop


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Warm structured logging, optional Redis waggle relay, and persistence clients."""

    configure_logging(level="INFO")
    await init_db()
    await ensure_collections()
    relay_task: asyncio.Task[None] | None = None
    if settings.hive_waggle_relay_enabled:
        relay_task = asyncio.create_task(run_hive_waggle_relay_loop(), name="hive_waggle_relay")

    yield

    if relay_task is not None:
        relay_task.cancel()
        try:
            await relay_task
        except asyncio.CancelledError:
            pass

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

app.include_router(health_router.router, prefix="/health")
app.include_router(api_v1, prefix="/api/v1")

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin).strip() for origin in settings.cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
