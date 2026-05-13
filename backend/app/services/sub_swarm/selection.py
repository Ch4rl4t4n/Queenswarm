"""Bee selection helpers for routing workflow steps inside a sub-swarm."""

from __future__ import annotations

from collections.abc import Sequence

from app.models.agent import Agent
from app.models.enums import AgentRole
from app.services.hive_tier import is_fixed_orchestrator_agent


def pick_agent_for_step(
    members: Sequence[Agent],
    *,
    queen: Agent | None,
    preferred_role: AgentRole,
) -> Agent:
    """Prefer a member aligned with the step role, then the queen, then any bee.

    Args:
        members: Active ``Agent`` rows attached to the sub-swarm.
        queen: Optional queen anchor for fallback routing.
        preferred_role: Role requested by the workflow step.

    Returns:
        The ORM row that should execute the step.

    Raises:
        ValueError: If the colony has no runnable members.
    """

    members = tuple(b for b in members if not is_fixed_orchestrator_agent(b))
    queen = queen if queen is None or not is_fixed_orchestrator_agent(queen) else None

    for bee in members:
        if bee.role == preferred_role:
            return bee
    if queen is not None:
        return queen
    if members:
        return members[0]
    msg = "Sub-swarm has no agents to execute workflow steps."
    raise ValueError(msg)


__all__ = ["pick_agent_for_step"]
