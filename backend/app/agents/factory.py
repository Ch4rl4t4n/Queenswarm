"""Factory mapping SQL ``Agent`` identities to runnable bee classes."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.agents.bees.generic import GenericBee
from app.agents.cost_governor import CostGovernor
from app.models.agent import Agent
from app.models.enums import AgentRole

_REGISTRY: dict[AgentRole, type[BaseAgent]] = {}

_DEFAULT_INITIALIZED = False


def _prime_defaults() -> None:
    """Register ``GenericBee`` for every enumerated role lazily."""

    global _DEFAULT_INITIALIZED  # noqa: PLW0603 — module singleton initializer
    if _DEFAULT_INITIALIZED:
        return
    for role in AgentRole:
        _REGISTRY.setdefault(role, GenericBee)
    _DEFAULT_INITIALIZED = True


def register_specialist(role: AgentRole, implementation: type[BaseAgent]) -> None:
    """Allow LangGraph loaders to supersede placeholders per colony recipe.

    Args:
        role: Swarm specialization key.
        implementation: Concrete :class:`~app.agents.base_agent.BaseAgent` subclass.
    """

    _prime_defaults()
    _REGISTRY[role] = implementation


def instantiate_agent(
    *,
    db: AsyncSession,
    agent_row: Agent,
    cost_governor: CostGovernor | None = None,
) -> BaseAgent:
    """Hydrate runtime bees honoring stored ``Agent.role`` assignments.

    Args:
        db: Async SQL session shared with callers orchestrating pollen writes.
        agent_row: ORM skeleton containing hive membership + pollen totals.
        cost_governor: Optional mocked governor during simulations.

    Returns:
        Specialized :class:`BaseAgent` derivative (defaults to ``GenericBee``).
    """

    _prime_defaults()
    impl = _REGISTRY.get(agent_row.role, GenericBee)
    return impl(db=db, agent_record=agent_row, cost_governor=cost_governor)


__all__ = ["instantiate_agent", "register_specialist"]
