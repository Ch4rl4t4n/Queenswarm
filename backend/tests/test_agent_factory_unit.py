"""Factory + registration coverage for swarm bees."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import MagicMock

import pytest

from app.agents.base_agent import BaseAgent
from app.agents.bees.generic import GenericBee
from app.agents.cost_governor import BudgetExceededError, CostGovernor
from app.agents.decorators import with_rapid_loop
from app.agents.factory import instantiate_agent, register_specialist
from app.models.enums import AgentRole


class _EchoBee(BaseAgent):
    """Ultra-light specialist used only inside unit tests."""

    async def execute(
        self,
        *,
        payload: dict[str, object],
        task_id: uuid.UUID | None = None,
    ) -> dict[str, object]:
        return {"handled_by": "_EchoBee", "slug": payload.get("slug")}


@pytest.fixture
def mock_session() -> MagicMock:
    """Async SQLAlchemy session stand-in."""

    return MagicMock(name="session")


@pytest.fixture
def hive_agent_stub() -> MagicMock:
    """Lightweight surrogate that satisfies factories without DB IO."""

    record = MagicMock()
    record.id = uuid.uuid4()
    record.role = AgentRole.LEARNER
    record.swarm_id = uuid.uuid4()
    record.pollen_points = 10.5
    return record


@pytest.mark.asyncio
async def test_instantiate_agent_defaults_to_generic_bee(
    mock_session: MagicMock,
    hive_agent_stub: MagicMock,
) -> None:
    """Hive rows without specialization should instantiate ``GenericBee``."""

    bee = instantiate_agent(db=mock_session, agent_row=hive_agent_stub)
    assert isinstance(bee, GenericBee)
    assert bee.agent_id == hive_agent_stub.id


@pytest.mark.asyncio
async def test_register_specialist_overrides_placeholder(
    mock_session: MagicMock,
    hive_agent_stub: MagicMock,
) -> None:
    """Registrar replays colony-specific subclasses per ``AgentRole``."""

    hive_agent_stub.role = AgentRole.EVALUATOR
    register_specialist(AgentRole.EVALUATOR, _EchoBee)
    try:
        bee = instantiate_agent(db=mock_session, agent_row=hive_agent_stub)
        assert isinstance(bee, _EchoBee)
        payload = {"slug": "unit"}
        outcome = await bee.execute(payload=payload)
        assert outcome["handled_by"] == "_EchoBee"
    finally:
        register_specialist(AgentRole.EVALUATOR, GenericBee)


def test_cost_governor_daily_limit_blocks_runaway_spend(monkeypatch: pytest.MonkeyPatch) -> None:
    """Spend guard rejects launches after the capped envelope is breached."""

    monkeypatch.setattr("app.agents.cost_governor.settings.daily_budget_usd", 50.0, raising=False)
    gov = CostGovernor()

    class _HitSession:
        async def scalar(self, _stmt):  # noqa: ANN001
            return 60.0

    async def _runner() -> None:
        await gov.assert_can_spend(_HitSession())

    with pytest.raises(BudgetExceededError):
        asyncio.run(_runner())


def test_decorator_with_rapid_loop_propagates_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Decorator should surface ``asyncio.TimeoutError`` shorter than SLA."""

    monkeypatch.setattr("app.agents.decorators.settings.rapid_loop_timeout_sec", 1, raising=False)

    class _Bee:
        @with_rapid_loop
        async def slow_job(self) -> str:
            await asyncio.sleep(5)
            return "never"

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(_Bee().slow_job())
