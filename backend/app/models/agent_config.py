"""Persistent prompt/tool/output configuration for dynamic (UI-defined) bee instances."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, text as sa_text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.agent import Agent


class AgentConfig(Base, TimestampMixin):
    """Defines how a universal executor runs one agent row via LLM + tools."""

    __tablename__ = "agent_configs"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    system_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="You are a helpful AI agent.",
    )
    user_prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=sa_text("'[]'::jsonb"),
    )
    output_format: Mapped[str] = mapped_column(String(50), nullable=False, default="text")
    output_destination: Mapped[str] = mapped_column(String(200), nullable=False, default="dashboard")
    output_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=sa_text("'{}'::jsonb"),
    )
    schedule_type: Mapped[str] = mapped_column(String(50), nullable=False, default="on_demand")
    schedule_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    agent: Mapped["Agent"] = relationship(
        "Agent",
        foreign_keys=[agent_id],
        back_populates="agent_config_row",
        uselist=False,
    )

    def __repr__(self) -> str:
        """Return a terse operator-facing representation."""

        return f"AgentConfig(agent_id={self.agent_id!s}, format={self.output_format!r}, active={self.is_active})"


__all__ = ["AgentConfig"]
