"""Persistence model for curated tenant memory markdown files."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Hard DB ceiling — must match Alembic migration ck_curated_memory_char_count_max.
CURATED_MEMORY_DB_CHAR_CEILING = 24_000


class CuratedFileKindORM(StrEnum):
    """Persisted curated memory kinds."""

    MISSION = "mission"
    IDEAL_STATE = "ideal_state"
    SOUL = "soul"
    SKILLS_HIERARCHY = "skills_hierarchy"
    INSTRUCTIONS = "instructions"


class CuratedMemoryORM(Base):
    """Tenant-scoped markdown memory file used for Queen prompt bootstrap."""

    __tablename__ = "curated_memory"
    __table_args__ = (
        UniqueConstraint("tenant_id", "kind", name="uq_curated_memory_tenant_kind"),
        CheckConstraint(
            f"char_count <= {CURATED_MEMORY_DB_CHAR_CEILING}",
            name="ck_curated_memory_char_count_max",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[CuratedFileKindORM] = mapped_column(
        SQLEnum(
            CuratedFileKindORM,
            values_callable=lambda items: [item.value for item in items],
            native_enum=False,
            length=32,
        ),
        nullable=False,
    )
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("dashboard_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        """Return concise developer representation."""

        return f"CuratedMemoryORM(id={self.id!s}, tenant_id={self.tenant_id!s}, kind={self.kind.value!r})"


__all__ = ["CuratedFileKindORM", "CuratedMemoryORM"]
