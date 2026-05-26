"""Bee-hive FastAPI entrypoint tying PostgreSQL, pgvector embeddings, Neo4j, and Redis scaffolding."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app import __version__
from app.application.services.hive_waggle_relay import run_hive_waggle_relay_loop
from app.core.chroma_client import ensure_collections
from app.core.config import settings
from app.core.database import async_session, close_db, init_db
from app.core.logging import configure_logging, get_logger
from app.core.observability import configure_observability
from app.core.metrics import observe_scaling_event, refresh_celery_gauges, refresh_operative_agent_gauges, refresh_pattern_success_rate_gauges
from app.core.neo4j_client import close_neo4j
from app.core.readiness import set_readiness_draining
from app.core.redis_client import (
    close_redis,
    increment_minute_counter,
    refresh_distributed_lock,
    release_distributed_lock,
    try_acquire_distributed_lock,
)
from app.presentation.api.middleware.request_context import RequestContextMiddleware
from app.presentation.api.middleware.rate_limit import RateLimitMiddleware
from app.presentation.api.middleware.security_headers import SecurityHeadersMiddleware
from app.presentation.api.routers import health as health_router
from app.presentation.api.v1 import api_v1


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Warm structured logging, optional Redis waggle relay, and persistence clients."""

    hive_log = get_logger(__name__)

    configure_logging(
        level=settings.log_level,
        service_name=settings.log_service_name,
        environment=settings.log_environment,
        instance_id=settings.instance_id,
    )
    configure_observability()
    set_readiness_draining(False)
    await init_db()
    async with async_session() as session:
        from app.application.services.llm_runtime_credentials import refresh_llm_secret_cache
        from app.application.services.stripe_runtime_credentials import refresh_stripe_secret_cache
        from app.domain.recipes.marketplace_seeds import load_premium_marketplace_seeds

        await refresh_llm_secret_cache(session)
        await refresh_stripe_secret_cache(session)
        if settings.recipes_enabled:
            seeded = await load_premium_marketplace_seeds(session)
            if seeded:
                await session.commit()
                hive_log.info("premium_marketplace_seeds.loaded", count=seeded)
    await ensure_collections()
    relay_task: asyncio.Task[None] | None = None

    async def _run_scaling_guarded_relay() -> None:
        """Run waggle relay as a distributed singleton in scaling mode."""

        log = hive_log.bind(agent_id="hive_waggle_relay", swarm_id="global", task_id="scaling-lock")
        lock_name = "hive_waggle_relay"
        lock_owner = settings.instance_id
        renew_interval = float(settings.distributed_lock_renew_interval_sec)
        ttl_sec = int(settings.distributed_lock_ttl_sec)

        while True:
            acquired = await try_acquire_distributed_lock(lock_name, owner=lock_owner, ttl_sec=ttl_sec)
            if not acquired:
                await asyncio.sleep(min(max(renew_interval, 1.0), 10.0))
                continue

            log.info("hive_waggle_relay.lock_acquired", instance_id=settings.instance_id)
            observe_scaling_event(event="lock_acquired", instance_id=settings.instance_id)
            try:
                await increment_minute_counter("scaling_events", ttl_sec=7200)
            except Exception:  # noqa: BLE001
                pass
            relay_worker = asyncio.create_task(run_hive_waggle_relay_loop(), name="hive_waggle_relay_singleton")
            lost_lock = False
            try:
                while not relay_worker.done():
                    await asyncio.sleep(renew_interval)
                    ok = await refresh_distributed_lock(lock_name, owner=lock_owner, ttl_sec=ttl_sec)
                    if not ok:
                        lost_lock = True
                        log.warning("hive_waggle_relay.lock_lost", instance_id=settings.instance_id)
                        observe_scaling_event(event="lock_lost", instance_id=settings.instance_id)
                        try:
                            await increment_minute_counter("scaling_events", ttl_sec=7200)
                        except Exception:  # noqa: BLE001
                            pass
                        relay_worker.cancel()
                        break
                if relay_worker.done():
                    await relay_worker
            except asyncio.CancelledError:
                if lost_lock:
                    pass
                else:
                    relay_worker.cancel()
                    raise
            finally:
                if not lost_lock:
                    await release_distributed_lock(lock_name, owner=lock_owner)
                    observe_scaling_event(event="lock_released", instance_id=settings.instance_id)
                log.info("hive_waggle_relay.lock_released", instance_id=settings.instance_id)

    if settings.hive_waggle_relay_enabled:
        if settings.scaling_mode_enabled:
            relay_task = asyncio.create_task(_run_scaling_guarded_relay(), name="hive_waggle_relay_scaling_guard")
        else:
            relay_task = asyncio.create_task(run_hive_waggle_relay_loop(), name="hive_waggle_relay")

    async def _gauge_refresh_tick() -> None:
        async with async_session() as session:
            await refresh_operative_agent_gauges(session)
            await refresh_pattern_success_rate_gauges(session)
        await asyncio.to_thread(refresh_celery_gauges)

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

    async def _run_scaling_guarded_gauge_loop() -> None:
        """Run metric gauge refresh as distributed singleton when HA scaling is enabled."""

        log = hive_log.bind(agent_id="hive_gauge_loop", swarm_id="global", task_id="scaling-lock")
        lock_name = "hive_metric_gauge_refresh"
        lock_owner = settings.instance_id
        renew_interval = float(settings.distributed_lock_renew_interval_sec)
        ttl_sec = int(settings.distributed_lock_ttl_sec)

        while True:
            acquired = await try_acquire_distributed_lock(lock_name, owner=lock_owner, ttl_sec=ttl_sec)
            if not acquired:
                await asyncio.sleep(min(max(renew_interval, 1.0), 10.0))
                continue
            log.info("hive_metric_gauge_refresh.lock_acquired", instance_id=settings.instance_id)
            worker = asyncio.create_task(_gauge_loop(), name="hive_agent_metric_gauges_singleton")
            lost_lock = False
            try:
                while not worker.done():
                    await asyncio.sleep(renew_interval)
                    ok = await refresh_distributed_lock(lock_name, owner=lock_owner, ttl_sec=ttl_sec)
                    if not ok:
                        lost_lock = True
                        log.warning("hive_metric_gauge_refresh.lock_lost", instance_id=settings.instance_id)
                        worker.cancel()
                        break
                if worker.done():
                    await worker
            except asyncio.CancelledError:
                if not lost_lock:
                    worker.cancel()
                    raise
            finally:
                if not lost_lock:
                    await release_distributed_lock(lock_name, owner=lock_owner)
                log.info("hive_metric_gauge_refresh.lock_released", instance_id=settings.instance_id)

    if settings.scaling_mode_enabled and settings.ha_mode_enabled:
        gauge_task = asyncio.create_task(
            _run_scaling_guarded_gauge_loop(),
            name="hive_agent_metric_gauges_scaling_guard",
        )
    else:
        gauge_task = asyncio.create_task(_gauge_loop(), name="hive_agent_metric_gauges")

    yield

    set_readiness_draining(True, reason="shutdown")
    if settings.graceful_shutdown_drain_sec > 0:
        await asyncio.sleep(float(settings.graceful_shutdown_drain_sec))

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

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Emit structured logs and stable JSON response for unexpected failures."""

    hive_log = get_logger(__name__)
    hive_log.exception(
        "api.unhandled_exception",
        agent_id="api_server",
        swarm_id="global",
        task_id="unhandled_exception",
        path=request.url.path,
        method=request.method,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error.", "path": request.url.path})

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)
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
