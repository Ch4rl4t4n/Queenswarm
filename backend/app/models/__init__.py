"""ORM aggregate exports with lazy lookups plus an explicit mapper bootstrap."""

from __future__ import annotations

import importlib
from typing import Any

from app.models.enums import (
    AgentRole,
    AgentStatus,
    BudgetPeriod,
    SimulationResult,
    StepStatus,
    SwarmPurpose,
    TaskStatus,
    TaskType,
    WorkflowStatus,
)

_EXPORTABLE: dict[str, tuple[str, str]] = {
    "Agent": ("app.models.agent", "Agent"),
    "Budget": ("app.models.cost", "Budget"),
    "CostRecord": ("app.models.cost", "CostRecord"),
    "ImitationEvent": ("app.models.reward", "ImitationEvent"),
    "KnowledgeItem": ("app.models.knowledge", "KnowledgeItem"),
    "LearningLog": ("app.models.knowledge", "LearningLog"),
    "PollenReward": ("app.models.reward", "PollenReward"),
    "Recipe": ("app.models.recipe", "Recipe"),
    "Simulation": ("app.models.simulation", "Simulation"),
    "SubSwarm": ("app.models.swarm", "SubSwarm"),
    "Task": ("app.models.task", "Task"),
    "Workflow": ("app.models.workflow", "Workflow"),
    "WorkflowStep": ("app.models.workflow", "WorkflowStep"),
    "SoftDeleteMixin": ("app.models.base", "SoftDeleteMixin"),
    "TimestampMixin": ("app.models.base", "TimestampMixin"),
    "UUIDMixin": ("app.models.base", "UUIDMixin"),
    "Base": ("app.core.database", "Base"),
}

_MODEL_PACKAGES: tuple[str, ...] = (
    "app.models.swarm",
    "app.models.agent",
    "app.models.recipe",
    "app.models.workflow",
    "app.models.task",
    "app.models.reward",
    "app.models.knowledge",
    "app.models.simulation",
    "app.models.cost",
)

_MODELS_INITIALIZED = False


def load_all_models() -> None:
    """Import mapper modules exactly once so SQLAlchemy metadata is complete."""

    global _MODELS_INITIALIZED
    if _MODELS_INITIALIZED:
        return
    for pkg in _MODEL_PACKAGES:
        importlib.import_module(pkg)
    _MODELS_INITIALIZED = True


def __getattr__(name: str) -> Any:
    """Lazily resolve heavy ORM classes without pulling Settings during tests."""

    if name in _EXPORTABLE:
        module_path, attr = _EXPORTABLE[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = [
    "Agent",
    "AgentRole",
    "AgentStatus",
    "Budget",
    "BudgetPeriod",
    "Base",
    "CostRecord",
    "ImitationEvent",
    "KnowledgeItem",
    "LearningLog",
    "PollenReward",
    "Recipe",
    "Simulation",
    "SimulationResult",
    "SoftDeleteMixin",
    "StepStatus",
    "SubSwarm",
    "SwarmPurpose",
    "Task",
    "TaskStatus",
    "TaskType",
    "TimestampMixin",
    "UUIDMixin",
    "Workflow",
    "WorkflowStatus",
    "WorkflowStep",
    "load_all_models",
]
