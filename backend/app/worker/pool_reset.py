"""Recycle network pools after Celery prefork — inherited async sockets break asyncpg."""

from __future__ import annotations

import asyncio

from celery.signals import worker_process_init

from app.core.logging import get_logger

_logger = get_logger(__name__)


@worker_process_init.connect(weak=False)
def _reset_pools_after_prefork(**_kwargs: object) -> None:
    """Dispose SQLAlchemy + Redis + Neo4j singletons copied from the parent process.

    Celery's default ``prefork`` pool forks worker children from a parent that already
    imported ``app.core.database``. AsyncPG connections cannot be shared across that
    boundary, which surfaces as ``InterfaceError: another operation is in progress``.
    """

    async def _purge() -> None:
        from app.core.database import async_engine
        from app.core.neo4j_client import close_neo4j
        from app.core.redis_client import close_redis

        await async_engine.dispose()
        await close_redis()
        await close_neo4j()
        _logger.info("celery_worker.pools_reset_after_fork")

    asyncio.run(_purge())


__all__ = ["_reset_pools_after_prefork"]
