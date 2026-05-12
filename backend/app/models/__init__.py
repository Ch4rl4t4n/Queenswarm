"""ORM aggregate exports — lazy heavyweight imports keep enum-only paths lightweight."""

from __future__ import annotations

import importlib
from typing import Any

_EXPORTABLE: dict[str, tuple[str, str]] = {
    "Agent": ("app.models.agent", "Agent"),
    "AgentConfig": ("app.models.agent_config", "AgentConfig"),
    "AgentRole": ("app.models.enums", "AgentRole"),
    "AgentStatus": ("app.models.enums", "AgentStatus"),
    "Base": ("app.core.database", "Base"),
    "Budget": ("app.models.cost", "Budget"),
    "BudgetPeriod": ("app.models.enums", "BudgetPeriod"),
    "DashboardUser": ("app.models.dashboard_user", "DashboardUser"),
    "DashboardApiKey": ("app.models.dashboard_api_key", "DashboardApiKey"),
    "CostRecord": ("app.models.cost", "CostRecord"),
    "HiveAsyncRunLifecycle": ("app.models.enums", "HiveAsyncRunLifecycle"),
    "HiveAsyncWorkflowRun": ("app.models.hive_async_workflow_run", "HiveAsyncWorkflowRun"),
    "ImitationEvent": ("app.models.reward", "ImitationEvent"),
    "KnowledgeItem": ("app.models.knowledge", "KnowledgeItem"),
    "LearningLog": ("app.models.knowledge", "LearningLog"),
    "PollenReward": ("app.models.reward", "PollenReward"),
    "Recipe": ("app.models.recipe", "Recipe"),
    "Simulation": ("app.models.simulation", "Simulation"),
    "SimulationResult": ("app.models.enums", "SimulationResult"),
    "SoftDeleteMixin": ("app.models.base", "SoftDeleteMixin"),
    "StepStatus": ("app.models.enums", "StepStatus"),
    "SubSwarm": ("app.models.swarm", "SubSwarm"),
    "SwarmPurpose": ("app.models.enums", "SwarmPurpose"),
    "Task": ("app.models.task", "Task"),
    "TaskStatus": ("app.models.enums", "TaskStatus"),
    "TaskType": ("app.models.enums", "TaskType"),
    "TimestampMixin": ("app.models.base", "TimestampMixin"),
    "UUIDMixin": ("app.models.base", "UUIDMixin"),
    "Workflow": ("app.models.workflow", "Workflow"),
    "WorkflowStatus": ("app.models.enums", "WorkflowStatus"),
    "WorkflowStep": ("app.models.workflow", "WorkflowStep"),
}

_MODEL_PACKAGES: tuple[str, ...] = (
    "app.models.swarm",
    "app.models.agent",
    "app.models.agent_config",
    "app.models.recipe",
    "app.models.workflow",
    "app.models.task",
    "app.models.reward",
    "app.models.knowledge",
    "app.models.simulation",
    "app.models.cost",
    "app.models.hive_async_workflow_run",
    "app.models.dashboard_user",
    "app.models.dashboard_api_key",
)

_BOOTSTRAPPED = False


def load_all_models() -> None:
    """Import mapper modules exactly once so SQLAlchemy metadata is fully populated."""

    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    for pkg in _MODEL_PACKAGES:
        importlib.import_module(pkg)
    _BOOTSTRAPPED = True


def __getattr__(name: str) -> Any:
    """Expose ORM helpers lazily without forcing Settings resolution."""

    target = _EXPORTABLE.get(name)
    if target is None:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)

    module_path, attr = target
    module = importlib.import_module(module_path)
    value = getattr(module, attr)
    globals()[name] = value
    return value


__all__ = sorted(_EXPORTABLE.keys()) + ["load_all_models"]
