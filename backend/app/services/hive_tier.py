"""Resolve hive hierarchy tier (orchestrator vs dynamic managers/workers) from ORM rows."""

from __future__ import annotations

from typing import Any

from app.models.agent import Agent
from app.models.agent_config import AgentConfig

FIXED_ORCHESTRATOR_AGENT_NAME = "Orchestrator"


class OrchestratorInvariantViolationError(ValueError):
    """Guardrail emitted when swarm/factory helpers touch the seeded Orchestrator row."""


def is_fixed_orchestrator_agent(agent: Agent) -> bool:
    """Return True for the single seeded Orchestrator bee (never factory-managed)."""

    raw = agent.config if isinstance(agent.config, dict) else {}
    if raw.get("hive_fixed") is True:
        return True
    tier = str(raw.get("hive_tier", "")).strip().lower()
    if tier == "orchestrator":
        return True
    return agent.name.strip().lower() == FIXED_ORCHESTRATOR_AGENT_NAME.lower()


def normalize_output_config_hive_tier(oc: dict[str, Any] | None) -> str | None:
    """Read ``hive_tier`` from universal executor output JSON."""

    if not oc:
        return None
    tier = oc.get("hive_tier")
    if isinstance(tier, str) and tier.strip():
        return tier.strip().lower()
    return None


def resolve_hive_tier(*, agent: Agent, agent_config: AgentConfig | None) -> str | None:
    """Derive dashboard tier: orchestrator, manager, worker, or unknown."""

    if is_fixed_orchestrator_agent(agent):
        return "orchestrator"
    tier = normalize_output_config_hive_tier(
        agent_config.output_config if agent_config is not None else None,
    )
    return tier


__all__ = [
    "FIXED_ORCHESTRATOR_AGENT_NAME",
    "OrchestratorInvariantViolationError",
    "is_fixed_orchestrator_agent",
    "normalize_output_config_hive_tier",
    "resolve_hive_tier",
]
