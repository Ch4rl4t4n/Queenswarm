"""Recipe Library rows that promote verified workflows via semantic recall."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, case, func, text
from sqlalchemy import Float as SAFloat
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class Recipe(Base, TimestampMixin):
    """Battle-tested workflow template linked to Chroma embeddings."""

    __tablename__ = "recipes"

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic_tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    workflow_template: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_pollen_earned: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    embedding_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_by_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id"),
        nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    is_deprecated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    matched_workflows: Mapped[list["Workflow"]] = relationship(
        "Workflow",
        back_populates="recipe",
        foreign_keys="Workflow.matching_recipe_id",
    )

    @hybrid_property
    def success_rate(self) -> float:
        """Rolling success proportion for imitation weighting."""

        total = self.success_count + self.fail_count
        if total == 0:
            return 0.0
        return float(self.success_count / total)

    @success_rate.expression  # type: ignore[no-redef]
    def success_rate_expression(cls):  # noqa: N805
        """SQL expression exposing success rate filters for leaderboard queries."""

        denom = cls.success_count + cls.fail_count
        return case(
            (denom > 0, cls.success_count / func.cast(func.nullif(denom, 0), SAFloat)),
            else_=0.0,
        )

    @hybrid_property
    def is_battle_tested(self) -> bool:
        """True once the hive has exercised the recipe sufficiently with high fidelity."""

        return self.success_count >= 5 and self.success_rate >= 0.7

    @is_battle_tested.expression  # type: ignore[no-redef]
    def is_battle_tested_expression(cls):  # noqa: N805
        """SQL-friendly battle-tested signal for promotion queries."""

        denom = cls.success_count + cls.fail_count
        sr = case(
            (denom > 0, cls.success_count / func.cast(func.nullif(denom, 0), SAFloat)),
            else_=0.0,
        )
        return case((cls.success_count >= 5, sr >= 0.7), else_=False)

    def __repr__(self) -> str:
        """Return a concise debug representation of the recipe."""

        return (
            f"Recipe(id={self.id!s}, name={self.name!r}, "
            f"success_rate={self.success_rate:.2f})"
        )
