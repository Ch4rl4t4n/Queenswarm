"""Async SQLAlchemy engine and declarative base for PostgreSQL hive persistence."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, with_loader_criteria
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.tenant_context import get_current_tenant_uuid


def build_async_engine_kwargs(*, celery_worker: bool) -> dict[str, Any]:
    """Return ``create_async_engine`` kwargs for API (pooled) vs Celery (null pool)."""

    if celery_worker:
        return {"echo": False, "poolclass": NullPool}
    return {"echo": False, "pool_size": 20, "max_overflow": 10}


async_engine: AsyncEngine = create_async_engine(
    settings.postgres_url,
    **build_async_engine_kwargs(celery_worker=settings.queenswarm_celery_worker),
)

async_session = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    """Declarative ORM root for swarm task ledger, pollen, and hive sync tables."""


class TimestampMixin:
    """UUID primary key and UTC timestamps for auditable hive rows."""

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


@event.listens_for(AsyncSession.sync_session_class, "do_orm_execute")
def _apply_tenant_scope(execute_state):  # type: ignore[no-untyped-def]
    """Apply tenant filter to all tenant-scoped ORM entities."""

    if not execute_state.is_select:
        return
    tenant_uuid = get_current_tenant_uuid()
    if tenant_uuid is None:
        return
    statement = execute_state.statement
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if not getattr(cls, "__tenant_scoped__", False):
            continue
        statement = statement.options(
            with_loader_criteria(
                cls,
                lambda obj: obj.tenant_id == tenant_uuid,
                include_aliases=True,
            ),
        )
    execute_state.statement = statement


@event.listens_for(AsyncSession.sync_session_class, "before_flush")
def _autofill_tenant_id(session, flush_context, instances):  # type: ignore[no-untyped-def]
    """Backfill tenant_id on newly created tenant-scoped rows."""

    del flush_context, instances
    tenant_uuid = get_current_tenant_uuid()
    if tenant_uuid is None:
        return
    for obj in session.new:
        if not getattr(obj.__class__, "__tenant_scoped__", False):
            continue
        if getattr(obj, "tenant_id", None) is None:
            setattr(obj, "tenant_id", tenant_uuid)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped async database session dependency.

    Yields:
        AsyncSession wired to the shared async engine pool.
    """

    async with async_session() as session:
        yield session


async def init_db() -> None:
    """Create declared ORM tables in PostgreSQL (idempotent bootstrap)."""

    from app.models import load_all_models

    load_all_models()
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose the async engine cleanly on shutdown."""

    await async_engine.dispose()
