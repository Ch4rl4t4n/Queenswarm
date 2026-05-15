"""Supervisor orchestration service package."""

from app.application.services.supervisor.session_service import (
    SUPPORTED_SUB_AGENT_ROLES,
    append_operator_interaction,
    apply_session_control,
    apply_session_review,
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
from app.application.services.supervisor.skills import SkillLibrary
from app.application.services.supervisor.routine_service import (
    compute_next_run_at,
    create_supervisor_routine,
    list_supervisor_routines,
    run_due_routines_tick,
    trigger_supervisor_routine_now,
)

__all__ = [
    "SUPPORTED_SUB_AGENT_ROLES",
    "SharedContextService",
    "SkillLibrary",
    "append_operator_interaction",
    "apply_session_control",
    "apply_session_review",
    "compute_next_run_at",
    "coerce_runtime_mode",
    "create_supervisor_session",
    "get_supervisor_session",
    "infer_manager_slug_for_role",
    "infer_specialist_roles_for_role",
    "list_session_events",
    "list_supervisor_routines",
    "list_supervisor_sessions",
    "normalize_roles",
    "run_due_routines_tick",
    "trigger_supervisor_routine_now",
    "create_supervisor_routine",
]

