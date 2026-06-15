"""NP1 — Stakeholder Grill wizard: structured interview → brief artifact → optional session."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.mission_kanban import create_mission_triage_task
from app.application.services.supervisor.session_service import create_supervisor_session
from app.application.services.supervisor.shared_context import SharedContextService
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.outputs.engine import OutputEngine

_logger = get_logger(__name__)

GrillQuestionId = Literal[
    "problem",
    "audience",
    "success_metric",
    "compliance",
    "kill_criteria",
    "unknowns",
    "constraints",
    "differentiation",
    "risks",
    "evidence",
]


class StakeholderGrillQuestionOut(BaseModel):
    """One grill interview prompt."""

    model_config = ConfigDict(extra="ignore")

    id: GrillQuestionId
    title: str
    prompt: str
    hint: str = ""


class StakeholderGrillWizardOut(BaseModel):
    """Wizard snapshot for UI."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    questions: list[StakeholderGrillQuestionOut] = Field(default_factory=list)
    min_answer_chars: int = 12


class StakeholderGrillSubmitIn(BaseModel):
    """Operator answers keyed by question id."""

    model_config = ConfigDict(extra="forbid")

    answers: dict[str, str] = Field(default_factory=dict)
    title: str | None = Field(default=None, min_length=3, max_length=500)
    dispatch_session: bool = False


class StakeholderGrillSubmitOut(BaseModel):
    """Triage task + workspace deliverable (+ optional supervisor session)."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    task_id: str
    deliverable_id: str
    title: str
    brief_markdown: str
    href: str = "/tasks"
    supervisor_session_id: str | None = None
    session_href: str | None = None
    message: str = ""


GRILL_QUESTIONS: tuple[StakeholderGrillQuestionOut, ...] = (
    StakeholderGrillQuestionOut(
        id="problem",
        title="Problem / opportunity",
        prompt="What problem or opportunity are you addressing?",
        hint="One paragraph — no internal account numbers or PII.",
    ),
    StakeholderGrillQuestionOut(
        id="audience",
        title="Audience",
        prompt="Who is the primary user or stakeholder?",
        hint="Segments, roles, or personas that must benefit.",
    ),
    StakeholderGrillQuestionOut(
        id="success_metric",
        title="Success metric",
        prompt="What KPI or outcome defines success?",
        hint="Leading + lagging metrics if possible.",
    ),
    StakeholderGrillQuestionOut(
        id="compliance",
        title="Regulatory notes",
        prompt="Compliance, legal, or policy constraints?",
        hint="Anonymized — no internal policy numbers.",
    ),
    StakeholderGrillQuestionOut(
        id="kill_criteria",
        title="Kill criteria",
        prompt="What would make you stop, pivot, or not ship?",
        hint="Explicit no-go signals for stakeholders.",
    ),
    StakeholderGrillQuestionOut(
        id="unknowns",
        title="Open questions",
        prompt="Top unknowns that block a confident decision?",
        hint="Questions for grill-me follow-up in session.",
    ),
    StakeholderGrillQuestionOut(
        id="constraints",
        title="Constraints",
        prompt="Budget, timeline, team, or scope limits?",
        hint="Hard vs soft constraints.",
    ),
    StakeholderGrillQuestionOut(
        id="differentiation",
        title="Differentiation",
        prompt="Why this approach vs alternatives or status quo?",
        hint="Competitive or build-vs-buy angle.",
    ),
    StakeholderGrillQuestionOut(
        id="risks",
        title="Execution risks",
        prompt="Top 3 execution risks?",
        hint="Delivery, adoption, technical, or org risks.",
    ),
    StakeholderGrillQuestionOut(
        id="evidence",
        title="Sources to fetch",
        prompt="What evidence, URLs, or docs should Research Bee pull?",
        hint="Public sources only unless redacted.",
    ),
)

_SECTION_TITLES: dict[str, str] = {row.id: row.title for row in GRILL_QUESTIONS}


def compose_grill_wizard_snapshot() -> StakeholderGrillWizardOut:
    """Return static question set for the grill wizard."""

    if not settings.stakeholder_grill_wizard_enabled:
        return StakeholderGrillWizardOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            questions=[],
        )
    return StakeholderGrillWizardOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        questions=list(GRILL_QUESTIONS),
        min_answer_chars=12,
    )


def _validate_answers(answers: dict[str, str], *, min_chars: int) -> dict[str, str]:
    """Normalize and validate required answers."""

    normalized: dict[str, str] = {}
    missing: list[str] = []
    for question in GRILL_QUESTIONS:
        raw = str(answers.get(question.id) or "").strip()
        if len(raw) < min_chars:
            missing.append(question.title)
            continue
        normalized[question.id] = raw
    if missing:
        joined = ", ".join(missing[:4])
        suffix = "…" if len(missing) > 4 else ""
        raise ValueError(f"Answers too short or missing for: {joined}{suffix}")
    return normalized


def compose_grill_brief_markdown(
    answers: dict[str, str],
    *,
    title: str | None = None,
) -> tuple[str, str]:
    """Build stakeholder brief markdown and resolved title."""

    resolved_title = (title or "").strip() or "Stakeholder grill brief"
    lines = [
        f"# {resolved_title}",
        "",
        "_Generated by Stakeholder Grill wizard — verify-first, no PII._",
        "",
    ]
    for question in GRILL_QUESTIONS:
        body = answers.get(question.id, "").strip()
        if not body:
            continue
        lines.extend([f"## {_SECTION_TITLES[question.id]}", "", body, ""])
    lines.extend(
        [
            "## Verification gates",
            "",
            "- Critic APPROVE before stakeholder share.",
            "- Research session may extend with grill-me follow-ups.",
            "- Simulate-first — no live publish or bank data in LLM.",
            "",
        ],
    )
    return resolved_title, "\n".join(lines).strip() + "\n"


def _session_goal_from_brief(*, title: str, brief_markdown: str) -> str:
    """Compact supervisor goal referencing the grill artifact."""

    excerpt = brief_markdown[:2400]
    return (
        f"Stakeholder grill follow-up (verify-first).\n\n"
        f"Brief: {title}\n\n"
        f"Use grill-me to challenge assumptions, fill gaps, and produce a ≤400-word operator summary.\n\n"
        f"---\n{excerpt}\n---\n"
        f"Critic APPROVE before final. Simulate only."
    )


async def submit_stakeholder_grill_wizard(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    created_by_subject: str,
    body: StakeholderGrillSubmitIn,
) -> StakeholderGrillSubmitOut:
    """Persist brief to kanban triage + task workspace; optionally spawn research session."""

    if not settings.stakeholder_grill_wizard_enabled:
        raise ValueError("Stakeholder Grill wizard is disabled.")

    min_chars = compose_grill_wizard_snapshot().min_answer_chars
    answers = _validate_answers(body.answers, min_chars=min_chars)
    title, markdown = compose_grill_brief_markdown(answers, title=body.title)

    triage = await create_mission_triage_task(
        session,
        task_text=markdown,
        title=title,
        priority=6,
        swarm_id=None,
        skills=["grill-me", "decision-frameworks"],
        extra_payload={
            "grill_wizard": True,
            "grill_answers": answers,
        },
    )
    task_id = triage.task.id
    lineage_id = uuid.uuid4()

    deliverable = await OutputEngine.create_final_deliverable(
        session,
        lineage_id=lineage_id,
        markdown_body=markdown,
        structured={
            "format": "queenswarm.grill_brief.v1",
            "answers": answers,
            "task_id": str(task_id),
        },
        title_hint=title,
        slug_hint="stakeholder-grill-brief",
        tags=["grill-wizard", "stakeholder-brief", "np1"],
        voice_script=None,
        dashboard_user_id=dashboard_user_id,
        ballroom_session_id=None,
        mission_id=task_id,
        source_task_id=task_id,
    )

    supervisor_session_id: uuid.UUID | None = None
    session_href: str | None = None
    if body.dispatch_session:
        runtime_mode = "durable" if settings.supervisor_durable_mode_enabled else "inprocess"
        sup = await create_supervisor_session(
            session,
            goal=_session_goal_from_brief(title=title, brief_markdown=markdown),
            created_by_subject=created_by_subject,
            runtime_mode=runtime_mode,
            roles=["researcher", "critic"],
            shared_context=SharedContextService(),
            retrieval_contract="customer_history+policy+last_3_tasks",
            skill_slugs=["grill-me", "decision-frameworks", "context"],
            tenant_id=tenant_id,
            context_seed={
                "grill_wizard": True,
                "source_task_id": str(task_id),
                "deliverable_id": str(deliverable.id),
            },
        )
        supervisor_session_id = sup.id
        session_href = f"/agents#sessions?session={sup.id}"

    await session.flush()
    _logger.info(
        "stakeholder_grill_wizard.submitted",
        agent_id="stakeholder_grill_wizard",
        swarm_id=str(tenant_id),
        task_id=str(task_id),
        deliverable_id=str(deliverable.id),
        session_id=str(supervisor_session_id) if supervisor_session_id else None,
    )

    message = "Brief saved to Mission Kanban triage and task workspace."
    if supervisor_session_id is not None:
        message = f"{message} Research session started."

    return StakeholderGrillSubmitOut(
        ok=True,
        task_id=str(task_id),
        deliverable_id=str(deliverable.id),
        title=title,
        brief_markdown=markdown,
        href=f"/tasks?task={task_id}",
        supervisor_session_id=str(supervisor_session_id) if supervisor_session_id else None,
        session_href=session_href,
        message=message,
    )


__all__ = [
    "GRILL_QUESTIONS",
    "StakeholderGrillSubmitIn",
    "StakeholderGrillSubmitOut",
    "StakeholderGrillWizardOut",
    "compose_grill_brief_markdown",
    "compose_grill_wizard_snapshot",
    "submit_stakeholder_grill_wizard",
]
