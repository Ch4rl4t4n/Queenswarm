"""Factory mapping SQL ``Agent`` identities to runnable bee classes (Phase D registry)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.agents.bees.generic import GenericBee
from app.agents.bees.role_bees import (
    BlogWriterBee,
    EvaluatorBee,
    LearnerBee,
    MarketerBee,
    RecipeKeeperBee,
    ReporterBee,
    ScraperBee,
    SimulatorBee,
    SocialPosterBee,
    TraderBee,
)
from app.agents.cost_governor import CostGovernor
from app.models.agent import Agent
from app.models.enums import AgentRole
from app.services.hive_tier import FIXED_ORCHESTRATOR_AGENT_NAME, is_fixed_orchestrator_agent

_REGISTRY: dict[AgentRole, type[BaseAgent]] = {}

_ORCHESTRATOR_SINGLETON_NAME = FIXED_ORCHESTRATOR_AGENT_NAME.lower()

_DEFAULT_SPECIALISTS: dict[AgentRole, type[BaseAgent]] = {
    AgentRole.SCRAPER: ScraperBee,
    AgentRole.EVALUATOR: EvaluatorBee,
    AgentRole.SIMULATOR: SimulatorBee,
    AgentRole.REPORTER: ReporterBee,
    AgentRole.TRADER: TraderBee,
    AgentRole.MARKETER: MarketerBee,
    AgentRole.BLOG_WRITER: BlogWriterBee,
    AgentRole.SOCIAL_POSTER: SocialPosterBee,
    AgentRole.LEARNER: LearnerBee,
    AgentRole.RECIPE_KEEPER: RecipeKeeperBee,
}

_DEFAULT_INITIALIZED = False


def _prime_defaults() -> None:
    """Register role specialists lazily while allowing ``register_specialist`` overrides."""

    global _DEFAULT_INITIALIZED  # noqa: PLW0603 — module singleton initializer
    if _DEFAULT_INITIALIZED:
        return
    for role, impl in _DEFAULT_SPECIALISTS.items():
        _REGISTRY.setdefault(role, impl)
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
    disallow_fixed_orchestrator: bool = False,
) -> BaseAgent:
    """Hydrate runtime bees honoring stored ``Agent.role`` assignments.

    Args:
        db: Async SQL session shared with callers orchestrating pollen writes.
        agent_row: ORM skeleton containing hive membership + pollen totals.
        cost_governor: Optional mocked governor during simulations.
        disallow_fixed_orchestrator: When True, raises if the row is the seeded Orchestrator (sub-swarm graphs only).

    Returns:
        Specialized :class:`BaseAgent` derivative (Phase D defaults per ``AgentRole``).
    """

    if disallow_fixed_orchestrator and is_fixed_orchestrator_agent(agent_row):
        msg = (
            f"Agent {agent_row.name!r} ({_ORCHESTRATOR_SINGLETON_NAME}) is reserved for the hive mission pipeline — "
            "not for LangGraph step specialists."
        )
        raise ValueError(msg)

    _prime_defaults()
    impl = _REGISTRY.get(agent_row.role, GenericBee)
    return impl(db=db, agent_record=agent_row, cost_governor=cost_governor)


__all__ = ["instantiate_agent", "register_specialist"]
