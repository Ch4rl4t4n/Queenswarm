"""Spend caps for LLM bursts before swarm fan-out (Cost Governor tier)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.cost import CostRecord

logger = get_logger(__name__)


class BudgetExceededError(RuntimeError):
    """Emitted when accrued spend violates daily caps before work starts."""


class CostGovernor:
    """Rolling guardrail that aggregates ``CostRecord`` rows per UTC calendar day."""

    def __init__(self) -> None:
        """Create a reusable governor referencing global ``settings`` envelopes."""

        self._daily_limit = float(settings.daily_budget_usd)
        self._warning_ratio = float(settings.cost_warning_threshold)

    @staticmethod
    def _utc_day_start(reference: datetime | None = None) -> datetime:
        """Return UTC midnight anchoring Postgres ``created_at`` filters."""

        now = reference or datetime.now(tz=UTC)
        return now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    async def accrued_spend_today(self, session: AsyncSession) -> float:
        """Sum ``cost_usd`` entries recorded since UTC midnight."""

        boundary = self._utc_day_start()
        stmt = select(func.coalesce(func.sum(CostRecord.cost_usd), 0.0)).where(
            CostRecord.created_at >= boundary,
        )
        total = await session.scalar(stmt)
        return float(total or 0.0)

    async def assert_can_spend(self, session: AsyncSession, *, delta_usd: float = 0.0) -> None:
        """Guarantee another ``delta_usd`` burn will not exceed the daily ceiling.

        Args:
            session: Active async SQLAlchemy session.
            delta_usd: Incremental dollars about to be spent on the next LLM hop.

        Raises:
            BudgetExceededError: When the daily limit would be exceeded.
        """

        spent = await self.accrued_spend_today(session)
        projected = spent + max(delta_usd, 0.0)
        utilization = projected / self._daily_limit if self._daily_limit > 0 else 0.0
        if self._daily_limit > 0 and utilization >= self._warning_ratio:
            logger.warning(
                "cost_governor.near_limit",
                spent_usd=spent,
                daily_limit_usd=self._daily_limit,
                utilization_ratio=round(utilization, 3),
            )
        if self._daily_limit > 0 and projected > self._daily_limit:
            msg = (
                f"Daily budget {self._daily_limit:.2f} USD would be exceeded "
                f"(spent {spent:.2f} + delta {delta_usd:.2f})."
            )
            raise BudgetExceededError(msg)
