"""Cost governor lineage (LLM burns) and pooled budget envelopes."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SQEnum, Float, ForeignKey, Integer, String, case
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property

from app.core.database import Base, TimestampMixin
from app.models.enums import BudgetPeriod


class CostRecord(Base, TimestampMixin):
    """Per-call spend attribution for swarm agents and runnable tasks."""

    __tablename__ = "cost_records"

    agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False)

    def __repr__(self) -> str:
        """Return a concise debug representation for audit trails."""

        return (
            f"CostRecord(id={self.id!s}, model={self.llm_model!r}, cost_usd={self.cost_usd})"
        )


class Budget(Base, TimestampMixin):
    """Rolling financial guardrail windows enforced before fan-out bursts."""

    __tablename__ = "budgets"

    period: Mapped[BudgetPeriod] = mapped_column(
        SQEnum(
            BudgetPeriod,
            values_callable=lambda obj: [m.value for m in obj],
            native_enum=False,
            length=32,
        ),
        nullable=False,
    )
    limit_usd: Mapped[float] = mapped_column(Float, nullable=False)
    spent_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @hybrid_property
    def utilization_pct(self) -> float:
        """Percentage of approved budget consumed in the hive window."""

        if self.limit_usd <= 0:
            return 0.0
        return float((self.spent_usd / self.limit_usd) * 100.0)

    @utilization_pct.expression  # type: ignore[no-redef]
    def utilization_pct_expression(cls):  # noqa: N805
        """Queryable utilization signal for alerting hooks."""

        return case(
            (cls.limit_usd > 0, (cls.spent_usd / cls.limit_usd) * 100.0),
            else_=0.0,
        )

    def __repr__(self) -> str:
        """Return a concise debug representation of the capped budget."""

        return (
            f"Budget(id={self.id!s}, period={self.period.value!r}, "
            f"spent={self.spent_usd}/{self.limit_usd})"
        )
