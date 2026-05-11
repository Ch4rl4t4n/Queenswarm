"""Docker-backed simulation artifacts gating verified user-visible payloads."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Enum as SQEnum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.models.enums import SimulationResult


class Simulation(Base, TimestampMixin):
    """Sandbox run metadata; only simulations with ``confidence_pct > 70`` unblock humans."""

    __tablename__ = "simulations"

    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    scenario: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    result_type: Mapped[SimulationResult] = mapped_column(
        SQEnum(
            SimulationResult,
            values_callable=lambda obj: [m.value for m in obj],
            native_enum=False,
            length=32,
        ),
        nullable=False,
    )
    confidence_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    docker_container_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        """Return a concise debug representation of the simulation row."""

        return (
            f"Simulation(id={self.id!s}, result={self.result_type.value!r}, "
            f"confidence_pct={self.confidence_pct})"
        )
