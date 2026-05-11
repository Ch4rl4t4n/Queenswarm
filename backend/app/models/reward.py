"""Pollen ledger and imitation graph edges (Maynard-Cross learning substrate)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.agent import Agent


class PollenReward(Base, TimestampMixin):
    """Award line item crediting verified outcomes to a bee's pollen balance."""

    __tablename__ = "pollen_rewards"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id"),
        nullable=True,
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    source_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id"),
        nullable=True,
    )

    agent: Mapped["Agent"] = relationship(
        "Agent",
        back_populates="pollen_rewards",
        foreign_keys=[agent_id],
        overlaps="source_agent",
    )
    source_agent: Mapped["Agent | None"] = relationship(
        "Agent",
        foreign_keys=[source_agent_id],
        overlaps="agent",
    )

    def __repr__(self) -> str:
        """Return a concise debug representation of the pollen reward."""

        return f"PollenReward(id={self.id!s}, agent_id={self.agent_id!s}, amount={self.amount})"


class ImitationEvent(Base, TimestampMixin):
    """Directed edge capturing copier → exemplar behavior for recipe analytics."""

    __tablename__ = "imitation_events"

    copier_agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id"),
        nullable=False,
    )
    copied_agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id"),
        nullable=False,
    )
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recipes.id"),
        nullable=True,
    )
    outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)

    copier: Mapped["Agent"] = relationship(
        "Agent",
        foreign_keys=[copier_agent_id],
        overlaps="copied",
    )
    copied: Mapped["Agent"] = relationship(
        "Agent",
        foreign_keys=[copied_agent_id],
        overlaps="copier",
    )

    def __repr__(self) -> str:
        """Return a concise debug representation of the imitation event."""

        return (
            f"ImitationEvent(id={self.id!s}, "
            f"copier={self.copier_agent_id!s} → copied={self.copied_agent_id!s})"
        )
