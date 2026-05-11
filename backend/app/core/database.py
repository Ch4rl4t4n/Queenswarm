"""Async SQLAlchemy engine and declarative base for PostgreSQL hive persistence."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings


async_engine: AsyncEngine = create_async_engine(
    settings.postgres_url,
    echo=False,
    pool_size=20,
    max_overflow=10,
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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped async database session dependency.

    Yields:
        AsyncSession wired to the shared async engine pool.
    """

    async with async_session() as session:
        yield session


async def init_db() -> None:
    """Create declared ORM tables in PostgreSQL (idempotent bootstrap)."""

    import app.models  # noqa: F401

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose the async engine cleanly on shutdown."""

    await async_engine.dispose()
