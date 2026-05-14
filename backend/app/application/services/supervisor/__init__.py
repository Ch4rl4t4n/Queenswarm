"""Supervisor orchestration service package."""

from app.application.services.supervisor.session_service import (
    SUPPORTED_SUB_AGENT_ROLES,
    append_operator_interaction,
    apply_session_control,
    coerce_runtime_mode,
    create_supervisor_session,
    get_supervisor_session,
    list_session_events,
    list_supervisor_sessions,
    normalize_roles,
)
from app.application.services.supervisor.spawner import (
    infer_manager_slug_for_role,
    infer_specialist_roles_for_role,
)
from app.application.services.supervisor.shared_context import SharedContextService

__all__ = [
    "SUPPORTED_SUB_AGENT_ROLES",
    "SharedContextService",
    "append_operator_interaction",
    "apply_session_control",
    "coerce_runtime_mode",
    "create_supervisor_session",
    "get_supervisor_session",
    "infer_manager_slug_for_role",
    "infer_specialist_roles_for_role",
    "list_session_events",
    "list_supervisor_sessions",
    "normalize_roles",
]

