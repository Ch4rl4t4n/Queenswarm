"""Autonomous bee agent records (pollen ledger + swarm membership)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SQEnum, Float, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.enums import AgentRole, AgentStatus

if TYPE_CHECKING:
    from app.models.agent_config import AgentConfig
    from app.models.reward import PollenReward
    from app.models.swarm import SubSwarm
    from app.models.task import Task


class Agent(Base, TimestampMixin):
    """Single autonomous worker with pollen balance and swarm placement."""

    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    role: Mapped[AgentRole] = mapped_column(
        SQEnum(
            AgentRole,
            values_callable=lambda obj: [m.value for m in obj],
            native_enum=False,
            length=48,
        ),
        nullable=False,
    )
    status: Mapped[AgentStatus] = mapped_column(
        SQEnum(
            AgentStatus,
            values_callable=lambda obj: [m.value for m in obj],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=AgentStatus.IDLE,
    )
    swarm_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sub_swarms.id"),
        nullable=True,
    )
    config: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    pollen_points: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    performance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    swarm: Mapped["SubSwarm | None"] = relationship(
        "SubSwarm",
        back_populates="members",
        foreign_keys=[swarm_id],
    )
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="agent")
    agent_config_row: Mapped["AgentConfig | None"] = relationship(
        "AgentConfig",
        back_populates="agent",
        uselist=False,
    )
    pollen_rewards: Mapped[list["PollenReward"]] = relationship(
        "PollenReward",
        back_populates="agent",
        foreign_keys="PollenReward.agent_id",
    )

    def __repr__(self) -> str:
        """Return a concise debug representation of the agent."""

        return (
            f"Agent(id={self.id!s}, name={self.name!r}, role={self.role.value!r}, "
            f"pollen={self.pollen_points})"
        )


# Ensure Task is imported after Agent so relationship("Task") resolves during mapper configure.
from app.models.task import Task as _EnsureTaskRegistry  # noqa: E402, F401
