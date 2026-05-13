"""Generic pull-based export of orchestrator-delivered payloads for external integrations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExternalOutput(Base):
    """Immutable feed row written after a ballroom Orchestrator finishes step 7."""

    __tablename__ = "external_outputs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    dashboard_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dashboard_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mission_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    text_report: Mapped[str] = mapped_column(Text(), nullable=False)
    voice_script: Mapped[str | None] = mapped_column(Text(), nullable=True)
    output_metadata: Mapped[dict[str, Any]] = mapped_column(
        "output_metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    simulation_outcome: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(128)),
        nullable=False,
        server_default=text("ARRAY[]::varchar[]"),
    )

    def __repr__(self) -> str:
        """Return developer-safe preview."""

        return (
            f"ExternalOutput(id={self.id!s}, user_id={self.dashboard_user_id!s}, mission_id={self.mission_id!s})"
        )


__all__ = ["ExternalOutput"]
