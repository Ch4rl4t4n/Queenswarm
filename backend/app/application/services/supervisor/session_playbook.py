"""Convert verified supervisor sessions into Recipe Library operator playbooks."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.recipe_write import (
    RecipeWriteConflictError,
    RecipeWritePayloadTooLargeError,
    create_recipe_entry,
)
from app.application.services.supervisor.runtime import normalize_role
from app.application.services.supervisor.session_playbook_config import (
    auto_save_mark_verified_on_approve,
    auto_save_playbook_on_approve_enabled,
)
from app.application.services.supervisor.session_service import derive_sub_goal
from app.common.schemas.recipes_write import RecipeCreateBody
from app.core.config import settings
from app.infrastructure.persistence.models.enums import AgentRole
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession
from app.infrastructure.persistence.models.tenant import Tenant

logger = structlog.get_logger(__name__)

SUPERVISOR_ROLE_TO_AGENT_ROLE: dict[str, AgentRole] = {
    "researcher": AgentRole.SCRAPER,
    "coder": AgentRole.SCRAPER,
    "browser_operator": AgentRole.SCRAPER,
    "critic": AgentRole.EVALUATOR,
    "designer": AgentRole.BLOG_WRITER,
}

VERIFIED_SESSION_STATUSES: frozenset[str] = frozenset({"completed", "stopped"})


class SessionPlaybookError(Exception):
    """Base error for session → playbook conversion."""


class SessionPlaybookNotReadyError(SessionPlaybookError):
    """Session lacks enough sub-agent structure for a recipe template."""


class SessionPlaybookNotVerifiedError(SessionPlaybookError):
    """Caller requested verified stamp on an unverified session."""


def map_supervisor_role_to_agent_role(role: str) -> AgentRole:
    """Map dashboard sub-agent role slugs onto Recipe Library agent roles."""

    key = normalize_role(role)
    return SUPERVISOR_ROLE_TO_AGENT_ROLE.get(key, AgentRole.REPORTER)


def _slugify_goal(goal: str) -> str:
    slug = re.sub(r"[^\w\s-]+", "", goal.strip().lower())
    slug = re.sub(r"\s+", "_", slug).strip("_")
    return slug[:60] or "session"


def suggest_playbook_name(*, goal: str, session_id: uuid.UUID) -> str:
    """Derive a unique-ish catalog name from session goal + id tail."""

    tail = session_id.hex[-6:]
    base = f"playbook_{_slugify_goal(goal)}_{tail}"
    return base[:200]


def _sub_agent_step_description(*, sub: SubAgentSession, goal: str) -> str:
    output = (sub.last_output or "").strip()
    if len(output) >= 8:
        return output[:4000]
    return derive_sub_goal(role=sub.role, goal=goal)[:4000]


def build_playbook_steps(
    *,
    session_row: SupervisorSession,
    sub_agents: list[SubAgentSession],
) -> list[dict[str, Any]]:
    """Build 3–7 recipe steps from one supervisor session envelope."""

    ordered = sorted(sub_agents, key=lambda row: int(row.spawn_order or 0))
    if not ordered:
        msg = "Supervisor session has no sub-agents to serialize."
        raise SessionPlaybookNotReadyError(msg)

    goal = str(session_row.goal or "").strip()
    context = dict(session_row.context_summary or {})
    steps: list[dict[str, Any]] = [
        {
            "step_order": 1,
            "description": (
                f"Supervisor orchestrates operator playbook for: {goal[:480]}"
                if goal
                else "Supervisor orchestrates verified operator playbook."
            ),
            "agent_role": AgentRole.REPORTER.value,
            "guardrails": {
                "source": "supervisor_session_playbook",
                "runtime_mode": str(session_row.runtime_mode or "inprocess"),
                "retrieval_contract": context.get("retrieval_contract"),
            },
            "evaluation_criteria": {
                "session_status": str(session_row.status or ""),
                "sub_agent_count": len(ordered),
            },
        },
    ]
    for idx, sub in enumerate(ordered, start=2):
        if idx > 7:
            break
        toolset = list(sub.toolset or [])
        memory = dict(sub.short_memory or {})
        steps.append(
            {
                "step_order": idx,
                "description": _sub_agent_step_description(sub=sub, goal=goal),
                "agent_role": map_supervisor_role_to_agent_role(sub.role).value,
                "guardrails": {
                    "supervisor_role": normalize_role(sub.role),
                    "toolset": toolset[:16],
                    "runtime_mode": str(sub.runtime_mode or session_row.runtime_mode or "inprocess"),
                },
                "evaluation_criteria": {
                    "sub_agent_status": str(sub.status or ""),
                    "completed": str(sub.status or "").lower() == "completed",
                    "self_heal_attempts": memory.get("self_heal_attempts"),
                },
            },
        )

    if len(steps) < 3:
        msg = "Playbook requires at least three steps (orchestrator + two sub-agents)."
        raise SessionPlaybookNotReadyError(msg)
    return steps


def build_playbook_workflow_template(
    *,
    session_row: SupervisorSession,
    sub_agents: list[SubAgentSession],
) -> dict[str, Any]:
    """Serialize session metadata into a Recipe Library workflow template."""

    context = dict(session_row.context_summary or {})
    return {
        "version": 1,
        "source": "supervisor_session_playbook",
        "supervisor_session_id": str(session_row.id),
        "task_text": str(session_row.goal or "").strip(),
        "runtime_mode": str(session_row.runtime_mode or "inprocess"),
        "session_status": str(session_row.status or ""),
        "requested_roles": list(context.get("requested_roles") or []),
        "retrieval_contract": context.get("retrieval_contract"),
        "skills_enabled": context.get("skills_enabled"),
        "steps": build_playbook_steps(session_row=session_row, sub_agents=sub_agents),
    }


def session_eligible_for_verified_playbook(session_row: SupervisorSession) -> bool:
    """Return True when session outcome is stable enough for verified catalog stamp."""

    status = str(session_row.status or "").strip().lower()
    if status in VERIFIED_SESSION_STATUSES:
        return True
    subs = list(getattr(session_row, "sub_agents", None) or [])
    if not subs:
        return False
    completed = sum(1 for sub in subs if str(sub.status or "").lower() == "completed")
    return completed >= max(1, len(subs) // 2)


async def save_supervisor_session_playbook(
    db: AsyncSession,
    *,
    session_row: SupervisorSession,
    name: str | None = None,
    description: str | None = None,
    topic_tags: list[str] | None = None,
    mark_verified: bool = False,
) -> tuple[Any, dict[str, Any]]:
    """Persist one supervisor session as a Recipe Library operator playbook."""

    subs = list(getattr(session_row, "sub_agents", None) or [])
    if mark_verified and not session_eligible_for_verified_playbook(session_row):
        msg = "Session is not completed enough to mark playbook as verified."
        raise SessionPlaybookNotVerifiedError(msg)

    template = build_playbook_workflow_template(session_row=session_row, sub_agents=subs)

    goal = str(session_row.goal or "").strip()
    recipe_name = (name or suggest_playbook_name(goal=goal, session_id=session_row.id)).strip()
    recipe_description = description
    if recipe_description is None:
        recipe_description = (
            f"Operator playbook captured from supervisor session {session_row.id} "
            f"({session_row.status}, {len(subs)} sub-agents)."
        )[:4000]

    tags = list(topic_tags or [])
    for tag in ("supervisor", "operator_playbook", str(session_row.runtime_mode or "inprocess")):
        if tag and tag not in tags:
            tags.append(tag)

    body = RecipeCreateBody(
        name=recipe_name,
        description=recipe_description,
        topic_tags=tags[:64],
        workflow_template=template,
        mark_verified=mark_verified,
    )
    recipe = await create_recipe_entry(
        db,
        body,
        swarm_id=str(session_row.swarm_id or ""),
        task_id=str(session_row.task_id or session_row.id),
    )
    meta = {
        "name": recipe.name,
        "step_count": len(template.get("steps") or []),
        "verified": mark_verified and recipe.verified_at is not None,
        "session_status": str(session_row.status or ""),
    }
    return recipe, meta


async def maybe_auto_save_playbook_on_approve(
    db: AsyncSession,
    *,
    tenant: Tenant,
    session_row: SupervisorSession,
) -> dict[str, Any] | None:
    """Fail-soft auto-save of operator playbook when tenant automation is enabled."""

    if not settings.recipes_enabled:
        return None
    if not auto_save_playbook_on_approve_enabled(tenant):
        return None

    summary = dict(session_row.context_summary or {})
    if summary.get("playbook_recipe_id"):
        return None

    mark_verified = auto_save_mark_verified_on_approve(tenant)
    try:
        recipe, meta = await save_supervisor_session_playbook(
            db,
            session_row=session_row,
            mark_verified=mark_verified,
            topic_tags=["supervisor", "operator_playbook", "auto_saved"],
        )
    except (SessionPlaybookNotReadyError, SessionPlaybookNotVerifiedError):
        return None
    except RecipeWriteConflictError:
        retry_name = f"{suggest_playbook_name(goal=str(session_row.goal or ''), session_id=session_row.id)[:190]}_{uuid.uuid4().hex[:4]}"
        try:
            recipe, meta = await save_supervisor_session_playbook(
                db,
                session_row=session_row,
                name=retry_name,
                mark_verified=mark_verified,
                topic_tags=["supervisor", "operator_playbook", "auto_saved"],
            )
        except (SessionPlaybookNotReadyError, SessionPlaybookNotVerifiedError, RecipeWriteConflictError):
            return None
    except RecipeWritePayloadTooLargeError as exc:
        logger.warning(
            "session_playbook.auto_save_payload_too_large",
            session_id=str(session_row.id),
            size_bytes=exc.size_bytes,
        )
        return None

    summary["playbook_recipe_id"] = str(recipe.id)
    summary["playbook_auto_saved_at"] = datetime.now(tz=UTC).isoformat()
    session_row.context_summary = summary
    await db.flush()
    return {
        "recipe_id": str(recipe.id),
        "recipe_name": recipe.name,
        "step_count": meta.get("step_count"),
        "verified": meta.get("verified"),
        "auto": True,
    }


__all__ = [
    "SessionPlaybookError",
    "SessionPlaybookNotReadyError",
    "SessionPlaybookNotVerifiedError",
    "build_playbook_steps",
    "build_playbook_workflow_template",
    "map_supervisor_role_to_agent_role",
    "save_supervisor_session_playbook",
    "maybe_auto_save_playbook_on_approve",
    "session_eligible_for_verified_playbook",
    "suggest_playbook_name",
]
