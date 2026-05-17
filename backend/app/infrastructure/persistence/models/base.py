"""Shared declarative helpers for swarm ORM mappings."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin as _TimestampMixin

TimestampMixin = _TimestampMixin
"""Re-exported from ``app.core.database`` for callers that compose hive models centrally."""


class UUIDMixin:
    """Primary key mixin using ``uuid.uuid4`` (one bee identity per row).

    Columns:
        id: Stateless UUID identifier shared across Postgres, Neo4j, and logs.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )


class SoftDeleteMixin:
    """Optional archival flag for swarm rows without destructive deletes.

    Columns:
        deleted_at: Timestamp marking logical removal.

    Attributes:
        is_deleted: True when ``deleted_at`` is populated.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        """Return True once the hive record was soft-retired."""

        return self.deleted_at is not None


class TenantScopedMixin:
    """Row-level tenant scope marker used by automatic query filters."""

    __tenant_scoped__ = True
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


__all__ = ["Base", "TimestampMixin", "UUIDMixin", "SoftDeleteMixin", "TenantScopedMixin"]
