"""Sub-swarm colony metadata (local hive mind + global sync cadence)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum as SQEnum, Float, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.database import Base, TimestampMixin
from app.models.enums import SwarmPurpose


class SubSwarm(Base, TimestampMixin):
    """Decentralized bee colony with local JSON memory and periodic global sync."""

    __tablename__ = "sub_swarms"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    purpose: Mapped[SwarmPurpose] = mapped_column(
        SQEnum(
            SwarmPurpose,
            values_callable=lambda obj: [m.value for m in obj],
            native_enum=False,
            length=32,
        ),
        nullable=False,
    )
    local_memory: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    queen_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", use_alter=True, name="fk_sub_swarms_queen_agent_id"),
        nullable=True,
    )
    last_global_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    total_pollen: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    members: Mapped[list["Agent"]] = relationship(
        "Agent",
        back_populates="swarm",
        foreign_keys="Agent.swarm_id",
    )
    queen: Mapped["Agent | None"] = relationship(
        "Agent",
        foreign_keys=[queen_agent_id],
        uselist=False,
    )
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="swarm")

    @property
    def needs_sync(self) -> bool:
        """True when the hive has not synced within ``HIVE_SYNC_INTERVAL_SEC``."""

        if self.last_global_sync_at is None:
            return True
        now = datetime.now(UTC)
        ref = self.last_global_sync_at
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=UTC)
        elapsed = (now - ref).total_seconds()
        return elapsed >= float(settings.hive_sync_interval_sec)

    def __repr__(self) -> str:
        """Return a concise debug representation of the sub-swarm."""

        return (
            f"SubSwarm(id={self.id!s}, name={self.name!r}, "
            f"purpose={self.purpose.value!r}, members={self.member_count})"
        )
