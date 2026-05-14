"""Bee-hive FastAPI entrypoint tying PostgreSQL, pgvector embeddings, Neo4j, and Redis scaffolding."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app import __version__
from app.application.services.hive_waggle_relay import run_hive_waggle_relay_loop
from app.core.chroma_client import ensure_collections
from app.core.config import settings
from app.core.database import async_session, close_db, init_db
from app.core.logging import configure_logging, get_logger
from app.core.metrics import refresh_operative_agent_gauges
from app.core.neo4j_client import close_neo4j
from app.core.redis_client import close_redis
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.api.routers import health as health_router
from app.api.v1 import api_v1


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Warm structured logging, optional Redis waggle relay, and persistence clients."""

    hive_log = get_logger(__name__)

    configure_logging(level="INFO")
    await init_db()
    async with async_session() as session:
        from app.application.services.llm_runtime_credentials import refresh_llm_secret_cache

        await refresh_llm_secret_cache(session)
    await ensure_collections()
    relay_task: asyncio.Task[None] | None = None
    if settings.hive_waggle_relay_enabled:
        relay_task = asyncio.create_task(run_hive_waggle_relay_loop(), name="hive_waggle_relay")

    async def _gauge_refresh_tick() -> None:
        async with async_session() as session:
            await refresh_operative_agent_gauges(session)

    async def _gauge_loop() -> None:
        while True:
            try:
                await _gauge_refresh_tick()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — observability loop must survive ORM stalls
                hive_log.warning(
                    "metrics.agent_gauge_refresh_failed",
                    agent_id="api_lifespan",
                    swarm_id="global",
                    task_id="gauge_tick",
                    error=str(exc),
                )
            await asyncio.sleep(25.0)

    gauge_task = asyncio.create_task(_gauge_loop(), name="hive_agent_metric_gauges")

    yield

    gauge_task.cancel()
    try:
        await gauge_task
    except asyncio.CancelledError:
        pass

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
    title="Queenswarm API",
    description="🐝 AI Agent Swarm — Dynamic. Autonomous. Unstoppable.",
    version=__version__,
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
