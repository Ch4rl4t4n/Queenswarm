"""NP5 — Trading thesis brief wizard: calibrated belief → risk preflight artifact."""

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

ThesisQuestionId = Literal[
    "market",
    "implied_probability",
    "your_edge",
    "position_size_cap",
    "kill_criteria",
    "paper_preflight",
]


class ThesisQuestionOut(BaseModel):
    """One trading thesis interview prompt."""

    model_config = ConfigDict(extra="ignore")

    id: ThesisQuestionId
    title: str
    prompt: str
    hint: str = ""


THESIS_QUESTIONS: tuple[ThesisQuestionOut, ...] = (
    ThesisQuestionOut(
        id="market",
        title="Market / event",
        prompt="Which market or event are you evaluating? Include platform and resolution date if known.",
        hint="Example: Polymarket — US election turnout > 65% by Nov 2026.",
    ),
    ThesisQuestionOut(
        id="implied_probability",
        title="Implied probability",
        prompt="What probability does the market imply today (%) and how did you derive it?",
        hint="Use mid-price or order book — not a gut feel.",
    ),
    ThesisQuestionOut(
        id="your_edge",
        title="Your edge",
        prompt="Why do you disagree with the market? Cite evidence or model inputs.",
        hint="Calibrated beliefs only — what would change your mind?",
    ),
    ThesisQuestionOut(
        id="position_size_cap",
        title="Position size cap",
        prompt="Maximum stake ($ or % portfolio) you will risk on this thesis.",
        hint="Hard cap — live lane blocked without this.",
    ),
    ThesisQuestionOut(
        id="kill_criteria",
        title="Kill criteria",
        prompt="When do you exit or abandon the thesis (price, news, time)?",
        hint="Include stop-loss logic and invalidation signals.",
    ),
    ThesisQuestionOut(
        id="paper_preflight",
        title="Paper preflight",
        prompt="Paper lane status: have you simulated this thesis? Link session or note gaps.",
        hint="Live requires real-money-risk-gate after paper review.",
    ),
)


class TradingThesisWizardOut(BaseModel):
    """Wizard snapshot for UI."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    questions: list[ThesisQuestionOut] = Field(default_factory=list)
    min_answer_chars: int = 10
    paper_cockpit_href: str = "/apps-tools/trading-automation?section=cockpit#trading-cockpit"
    live_gate_skill: str = "real-money-risk-gate"


class TradingThesisSubmitIn(BaseModel):
    """Operator answers keyed by question id."""

    model_config = ConfigDict(extra="forbid")

    answers: dict[str, str] = Field(default_factory=dict)
    title: str | None = Field(default=None, min_length=3, max_length=500)
    dispatch_session: bool = False


class TradingThesisSubmitOut(BaseModel):
    """Triage task + workspace deliverable (+ optional evaluator session)."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    task_id: str
    deliverable_id: str
    title: str
    brief_markdown: str
    href: str = "/tasks"
    supervisor_session_id: str | None = None
    session_href: str | None = None
    paper_cockpit_href: str = "/apps-tools/trading-automation?section=cockpit#trading-cockpit"
    message: str = ""


_SECTION_TITLES: dict[str, str] = {row.id: row.title for row in THESIS_QUESTIONS}


def compose_trading_thesis_wizard_snapshot() -> TradingThesisWizardOut:
    """Return static question set for the trading thesis wizard."""

    if not settings.trading_thesis_wizard_enabled:
        return TradingThesisWizardOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            questions=[],
        )
    return TradingThesisWizardOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        questions=list(THESIS_QUESTIONS),
        min_answer_chars=10,
    )


def _validate_answers(answers: dict[str, str], *, min_chars: int) -> dict[str, str]:
    """Normalize and validate required answers."""

    normalized: dict[str, str] = {}
    missing: list[str] = []
    for question in THESIS_QUESTIONS:
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


def compose_trading_thesis_brief_markdown(
    answers: dict[str, str],
    *,
    title: str | None = None,
) -> tuple[str, str]:
    """Build trading thesis brief markdown and resolved title."""

    resolved_title = (title or "").strip() or "Trading thesis brief"
    lines = [
        f"# {resolved_title}",
        "",
        "_Generated by Trading Thesis wizard — probabilities not guesses; simulate-first._",
        "",
    ]
    for question in THESIS_QUESTIONS:
        body = answers.get(question.id, "").strip()
        if not body:
            continue
        lines.extend([f"## {_SECTION_TITLES[question.id]}", "", body, ""])
    lines.extend(
        [
            "## Risk preflight gates",
            "",
            "- Paper lane review required before live stake.",
            "- Live execution blocked until `real-money-risk-gate` operator approval.",
            "- Critic APPROVE before sharing thesis externally.",
            "- No bank PII or account numbers in LLM context.",
            "",
            "## Next steps",
            "",
            "1. Run polymarket-prediction-evaluator session on this brief.",
            "2. Confirm paper cockpit P&L alignment.",
            "3. Operator OK for live only after gates pass.",
            "",
        ],
    )
    return resolved_title, "\n".join(lines).strip() + "\n"


def _session_goal_from_brief(*, title: str, brief_markdown: str) -> str:
    """Compact supervisor goal referencing the thesis artifact."""

    excerpt = brief_markdown[:2400]
    return (
        f"Trading thesis evaluation (verify-first, no live orders).\n\n"
        f"Thesis: {title}\n\n"
        f"Use polymarket-prediction-evaluator to score edge vs implied probability.\n"
        f"real-money-risk-gate must block any live execution.\n\n"
        f"---\n{excerpt}\n---\n"
        f"Critic APPROVE before operator summary (≤400 words). Simulate only."
    )


async def submit_trading_thesis_wizard(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    created_by_subject: str,
    body: TradingThesisSubmitIn,
) -> TradingThesisSubmitOut:
    """Persist thesis to kanban triage + task workspace; optionally spawn evaluator session."""

    if not settings.trading_thesis_wizard_enabled:
        raise ValueError("Trading Thesis wizard is disabled.")

    min_chars = compose_trading_thesis_wizard_snapshot().min_answer_chars
    answers = _validate_answers(body.answers, min_chars=min_chars)
    title, markdown = compose_trading_thesis_brief_markdown(answers, title=body.title)

    triage = await create_mission_triage_task(
        session,
        task_text=markdown,
        title=title,
        priority=7,
        swarm_id=None,
        skills=["polymarket-prediction-evaluator", "real-money-risk-gate", "decision-frameworks"],
        extra_payload={
            "trading_thesis_wizard": True,
            "thesis_answers": answers,
        },
    )
    task_id = triage.task.id
    lineage_id = uuid.uuid4()

    deliverable = await OutputEngine.create_final_deliverable(
        session,
        lineage_id=lineage_id,
        markdown_body=markdown,
        structured={
            "format": "queenswarm.trading_thesis.v1",
            "answers": answers,
            "task_id": str(task_id),
        },
        title_hint=title,
        slug_hint="trading-thesis-brief",
        tags=["trading-thesis", "np5", "risk-preflight"],
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
            skill_slugs=[
                "polymarket-prediction-evaluator",
                "real-money-risk-gate",
                "decision-frameworks",
                "context",
            ],
            tenant_id=tenant_id,
            context_seed={
                "trading_thesis_wizard": True,
                "source_task_id": str(task_id),
                "deliverable_id": str(deliverable.id),
            },
        )
        supervisor_session_id = sup.id
        session_href = f"/agents#sessions?session={sup.id}"

    await session.flush()
    _logger.info(
        "trading_thesis_wizard.submitted",
        agent_id="trading_thesis_wizard",
        swarm_id=str(tenant_id),
        task_id=str(task_id),
        deliverable_id=str(deliverable.id),
        session_id=str(supervisor_session_id) if supervisor_session_id else None,
    )

    message = "Thesis brief saved to Mission Kanban triage and task workspace."
    if supervisor_session_id is not None:
        message = f"{message} Evaluator session started."

    return TradingThesisSubmitOut(
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
    "THESIS_QUESTIONS",
    "TradingThesisSubmitIn",
    "TradingThesisSubmitOut",
    "TradingThesisWizardOut",
    "compose_trading_thesis_brief_markdown",
    "compose_trading_thesis_wizard_snapshot",
    "submit_trading_thesis_wizard",
]
