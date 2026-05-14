"""ORM aggregate exports — lazy heavyweight imports keep enum-only paths lightweight."""

from __future__ import annotations

import importlib
from typing import Any

_EXPORTABLE: dict[str, tuple[str, str]] = {
    "Agent": ("app.infrastructure.persistence.models.agent", "Agent"),
    "AgentConfig": ("app.infrastructure.persistence.models.agent_config", "AgentConfig"),
    "AgentRole": ("app.infrastructure.persistence.models.enums", "AgentRole"),
    "AgentStatus": ("app.infrastructure.persistence.models.enums", "AgentStatus"),
    "Base": ("app.core.database", "Base"),
    "Budget": ("app.infrastructure.persistence.models.cost", "Budget"),
    "BudgetPeriod": ("app.infrastructure.persistence.models.enums", "BudgetPeriod"),
    "ConnectorVaultEntry": ("app.infrastructure.persistence.models.connector_vault_entry", "ConnectorVaultEntry"),
    "DashboardUser": ("app.infrastructure.persistence.models.dashboard_user", "DashboardUser"),
    "DynamicConnector": ("app.infrastructure.persistence.models.dynamic_connector", "DynamicConnector"),
    "ExternalProject": ("app.infrastructure.persistence.models.external_project", "ExternalProject"),
    "ExternalProjectApiKey": ("app.infrastructure.persistence.models.external_project", "ExternalProjectApiKey"),
    "ExternalProjectRunAudit": ("app.infrastructure.persistence.models.external_project", "ExternalProjectRunAudit"),
    "DashboardApiKey": ("app.infrastructure.persistence.models.dashboard_api_key", "DashboardApiKey"),
    "OperatorExternalApi": ("app.infrastructure.persistence.models.operator_external_api", "OperatorExternalApi"),
    "CostRecord": ("app.infrastructure.persistence.models.cost", "CostRecord"),
    "HiveAsyncRunLifecycle": ("app.infrastructure.persistence.models.enums", "HiveAsyncRunLifecycle"),
    "HiveAsyncWorkflowRun": ("app.infrastructure.persistence.models.hive_async_workflow_run", "HiveAsyncWorkflowRun"),
    "HiveLlmSecret": ("app.infrastructure.persistence.models.hive_llm_secret", "HiveLlmSecret"),
    "ImitationEvent": ("app.infrastructure.persistence.models.reward", "ImitationEvent"),
    "KnowledgeItem": ("app.infrastructure.persistence.models.knowledge", "KnowledgeItem"),
    "LearningLog": ("app.infrastructure.persistence.models.knowledge", "LearningLog"),
    "PollenReward": ("app.infrastructure.persistence.models.reward", "PollenReward"),
    "Recipe": ("app.infrastructure.persistence.models.recipe", "Recipe"),
    "Simulation": ("app.infrastructure.persistence.models.simulation", "Simulation"),
    "SimulationResult": ("app.infrastructure.persistence.models.enums", "SimulationResult"),
    "SubAgentSession": ("app.infrastructure.persistence.models.supervisor_session", "SubAgentSession"),
    "SupervisorSession": ("app.infrastructure.persistence.models.supervisor_session", "SupervisorSession"),
    "SupervisorSessionEvent": (
        "app.infrastructure.persistence.models.supervisor_session",
        "SupervisorSessionEvent",
    ),
    "TaskFinalDeliverable": ("app.infrastructure.persistence.models.task_final_deliverable", "TaskFinalDeliverable"),
    "SoftDeleteMixin": ("app.infrastructure.persistence.models.base", "SoftDeleteMixin"),
    "StepStatus": ("app.infrastructure.persistence.models.enums", "StepStatus"),
    "SubSwarm": ("app.infrastructure.persistence.models.swarm", "SubSwarm"),
    "SwarmPurpose": ("app.infrastructure.persistence.models.enums", "SwarmPurpose"),
    "Task": ("app.infrastructure.persistence.models.task", "Task"),
    "TaskStatus": ("app.infrastructure.persistence.models.enums", "TaskStatus"),
    "TaskType": ("app.infrastructure.persistence.models.enums", "TaskType"),
    "TimestampMixin": ("app.infrastructure.persistence.models.base", "TimestampMixin"),
    "UUIDMixin": ("app.infrastructure.persistence.models.base", "UUIDMixin"),
    "Workflow": ("app.infrastructure.persistence.models.workflow", "Workflow"),
    "WorkflowStatus": ("app.infrastructure.persistence.models.enums", "WorkflowStatus"),
    "WorkflowStep": ("app.infrastructure.persistence.models.workflow", "WorkflowStep"),
}

_MODEL_PACKAGES: tuple[str, ...] = (
    "app.infrastructure.persistence.models.swarm",
    "app.infrastructure.persistence.models.agent",
    "app.infrastructure.persistence.models.agent_config",
    "app.infrastructure.persistence.models.recipe",
    "app.infrastructure.persistence.models.workflow",
    "app.infrastructure.persistence.models.task",
    "app.infrastructure.persistence.models.task_final_deliverable",
    "app.infrastructure.persistence.models.reward",
    "app.infrastructure.persistence.models.knowledge",
    "app.infrastructure.persistence.models.simulation",
    "app.infrastructure.persistence.models.cost",
    "app.infrastructure.persistence.models.hive_async_workflow_run",
    "app.infrastructure.persistence.models.hive_llm_secret",
    "app.infrastructure.persistence.models.dashboard_user",
    "app.infrastructure.persistence.models.dashboard_api_key",
    "app.infrastructure.persistence.models.operator_external_api",
    "app.infrastructure.persistence.models.connector_vault_entry",
    "app.infrastructure.persistence.models.dynamic_connector",
    "app.infrastructure.persistence.models.external_project",
    "app.infrastructure.persistence.models.supervisor_session",
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
