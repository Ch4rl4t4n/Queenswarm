"""Runtime execution helpers for dynamic supervisor sub-agents."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.shared_context import SharedContextService
from app.application.services.supervisor.skills import SkillLibrary
from app.infrastructure.persistence.models.supervisor_session import (
    SubAgentSession,
    SupervisorSession,
    SupervisorSessionEvent,
)

ROLE_TO_DEFAULT_TOOLSET: dict[str, list[str]] = {
    "researcher": ["search", "read", "summarize"],
    "coder": ["analyze_code", "edit_code", "run_tests"],
    "browser_operator": ["browse", "snapshot", "interact"],
    "critic": ["review", "risk_assessment", "verification"],
    "designer": ["wireframe", "ui_review", "design_tokens"],
}


def normalize_role(role: str) -> str:
    """Normalize role slug for deterministic orchestration records."""

    return role.strip().lower().replace("-", "_")


def default_toolset_for_role(role: str) -> list[str]:
    """Return default toolset for a known role."""

    key = normalize_role(role)
    return list(ROLE_TO_DEFAULT_TOOLSET.get(key, ["analyze", "report"]))


async def append_event(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    sub_agent: SubAgentSession | None,
    event_type: str,
    message: str,
    level: str = "info",
    payload: dict[str, Any] | None = None,
) -> SupervisorSessionEvent:
    """Append one structured event row for dashboard timelines."""

    row = SupervisorSessionEvent(
        supervisor_session_id=supervisor_session.id,
        sub_agent_session_id=sub_agent.id if sub_agent is not None else None,
        event_type=event_type.strip().lower(),
        message=message.strip(),
        level=level.strip().lower() or "info",
        payload=dict(payload or {}),
        occurred_at=datetime.now(tz=UTC),
    )
    db.add(row)
    await db.flush()
    return row


async def run_sub_agent_inprocess(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    sub_agent: SubAgentSession,
    shared_context: SharedContextService,
    skill_library: SkillLibrary | None = None,
) -> None:
    """Execute a lightweight in-process sub-agent cycle."""

    loader = skill_library or SkillLibrary()
    selected_skills = [
        str(item)
        for item in (sub_agent.short_memory or {}).get("skills", [])
        if isinstance(item, str) and item.strip()
    ]
    skill_prompt = loader.build_prompt_block(selected_skills)
    retrieval_contract = str((supervisor_session.context_summary or {}).get("retrieval_contract") or "").strip()
    retrieval_bundle = await shared_context.retrieve_context_bundle(
        db,
        supervisor_session_id=supervisor_session.id,
        query=supervisor_session.goal,
        contract=retrieval_contract,
    )
    retrieval_prompt = shared_context.render_bundle_for_prompt(retrieval_bundle)

    now = datetime.now(tz=UTC)
    sub_agent.status = "running"
    sub_agent.started_at = now
    await append_event(
        db,
        supervisor_session=supervisor_session,
        sub_agent=sub_agent,
        event_type="sub_agent_started",
        message=f"{sub_agent.role} started in in-process runtime.",
        payload={"runtime_mode": "inprocess"},
    )

    result_msg = (
        f"{sub_agent.role} processed goal: {supervisor_session.goal[:240]} "
        "and stored context for downstream agents. "
        f"skills={len(selected_skills)} retrieval_sections={len(retrieval_bundle.matched_sections)}"
    )
    sub_agent.last_output = result_msg
    sub_agent.short_memory = {
        **dict(sub_agent.short_memory or {}),
        "last_summary": result_msg,
        "processed_at": datetime.now(tz=UTC).isoformat(),
        "skills_prompt_block": skill_prompt[:4000],
        "retrieval_prompt_block": retrieval_prompt[:2500],
    }
    sub_agent.status = "completed"
    sub_agent.completed_at = datetime.now(tz=UTC)

    memory_result = await shared_context.write_step_context(
        supervisor_session_id=supervisor_session.id,
        sub_agent_session_id=sub_agent.id,
        role=sub_agent.role,
        goal=supervisor_session.goal,
        message=result_msg,
        payload={
            "runtime_mode": "inprocess",
            "skills": selected_skills,
            "retrieval_contract": retrieval_contract,
            "retrieval_sections": retrieval_bundle.matched_sections,
        },
    )
    await append_event(
        db,
        supervisor_session=supervisor_session,
        sub_agent=sub_agent,
        event_type="sub_agent_completed",
        message=f"{sub_agent.role} completed and wrote shared context.",
        payload={
            "runtime_mode": "inprocess",
            "vector_id": memory_result.vector_id,
            "graph_node_id": memory_result.graph_node_id,
        },
    )

