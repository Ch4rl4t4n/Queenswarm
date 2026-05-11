"""Scout-sourced knowledge blobs and post-task reflection logs."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class KnowledgeItem(Base, TimestampMixin):
    """Structured hive memory mirroring Chroma + Neo4j projections with decay."""

    __tablename__ = "knowledge_items"

    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    neo4j_node_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    topic_tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    decay_factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    def __repr__(self) -> str:
        """Return a concise debug representation of the knowledge item."""

        return (
            f"KnowledgeItem(id={self.id!s}, source_type={self.source_type!r}, "
            f"confidence={self.confidence_score})"
        )


class LearningLog(Base, TimestampMixin):
    """Captured reflection payloads emitted after imitation or reward events."""

    __tablename__ = "learning_logs"

    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"), nullable=False)
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id"),
        nullable=True,
    )
    insight_text: Mapped[str] = mapped_column(Text, nullable=False)
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    pollen_earned: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    agent: Mapped["Agent"] = relationship("Agent")

    def __repr__(self) -> str:
        """Return a concise debug representation of the learning log row."""

        return f"LearningLog(id={self.id!s}, agent_id={self.agent_id!s})"
