"""LOOP1 — Closed review loop: rubric score → self-heal revision → re-run."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.loop_guardrails_service import get_loop_guardrails_policy
from app.application.services.rubric_templates import evaluate_text_with_rubric, get_rubric_template
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)


class ClosedReviewLoopTurnOut(BaseModel):
    """One evaluate (+ optional revise) iteration."""

    model_config = ConfigDict(extra="ignore")

    turn: int
    score: float
    is_valid: bool
    passed: bool
    feedback: str = ""


class ClosedReviewLoopResultOut(BaseModel):
    """Final closed-loop outcome after up to max_turns iterations."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    passed: bool
    turns_used: int
    max_turns: int
    min_score: float
    min_score_label: str
    template_id: str
    template_name: str
    initial_text: str
    final_text: str
    iterations: list[ClosedReviewLoopTurnOut] = Field(default_factory=list)
    message: str = ""


class ClosedReviewLoopRunIn(BaseModel):
    """Operator request to run a scored closed review loop."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=8, max_length=12000)
    template_id: str = Field(min_length=2, max_length=64)
    max_turns: int | None = Field(default=None, ge=1, le=25)
    min_score: float | None = Field(default=None, ge=0.0, le=1.0)
    task_id: str | None = Field(default=None, max_length=64)


def _score_from_evaluation(evaluation: dict[str, Any]) -> float:
    """Normalize evaluator confidence to 0–1."""

    raw = evaluation.get("confidence")
    if isinstance(raw, (int, float)):
        return max(0.0, min(float(raw), 1.0))
    return 1.0 if bool(evaluation.get("is_valid")) else 0.0


def _turn_passed(*, evaluation: dict[str, Any], min_score: float) -> bool:
    """Return True when rubric pass threshold and min score both satisfied."""

    score = _score_from_evaluation(evaluation)
    template_threshold = float(evaluation.get("pass_threshold") or min_score)
    floor = max(min_score, template_threshold)
    return bool(evaluation.get("is_valid")) and score >= floor


async def _revise_text_from_feedback(
    session: AsyncSession,
    *,
    text: str,
    feedback: str,
    template_name: str,
    tenant_id: uuid.UUID | None,
    task_id: str | None,
) -> str:
    """Self-heal step — revise draft using critic feedback (single LLM hop)."""

    from app.core.llm_router import LiteLLMRouter

    router = LiteLLMRouter()
    messages = [
        {
            "role": "system",
            "content": (
                "You are a closed-loop copy editor. Revise the draft to address critic feedback. "
                "Preserve factual claims unless feedback flags them. Output ONLY the revised text."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Rubric: {template_name}\n\n"
                f"--- Draft ---\n{text.strip()}\n\n"
                f"--- Critic feedback ---\n{feedback.strip()}\n\n"
                "Revised draft:"
            ),
        },
    ]
    revised, _cost = await router.complete_single_model(
        session,
        model_name=settings.workflow_breaker_tertiary_model,
        messages=messages,
        max_tokens=2048,
        temperature=0.3,
        swarm_id=str(tenant_id) if tenant_id else "",
        task_id=task_id,
    )
    cleaned = str(revised or "").strip()
    return cleaned if len(cleaned) >= 8 else text


async def run_closed_review_loop(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    body: ClosedReviewLoopRunIn,
) -> ClosedReviewLoopResultOut:
    """Run LOOP1: evaluate → self-heal → re-run until pass or max turns."""

    if not settings.closed_review_loop_enabled:
        msg = "Closed Review Loop is disabled."
        raise ValueError(msg)

    template = get_rubric_template(body.template_id)
    if template is None:
        msg = f"Unknown rubric template: {body.template_id}"
        raise ValueError(msg)

    policy = await get_loop_guardrails_policy(session, tenant_id=tenant_id) if tenant_id else None
    max_turns = body.max_turns
    if max_turns is None:
        max_turns = policy.max_turns if policy is not None else settings.loop_guardrails_default_max_turns
    min_score = body.min_score
    if min_score is None:
        min_score = max(template.pass_threshold, policy.min_score if policy else template.pass_threshold)

    current_text = body.text.strip()
    iterations: list[ClosedReviewLoopTurnOut] = []
    swarm_id = str(tenant_id) if tenant_id else ""

    for turn in range(1, max_turns + 1):
        evaluation = await evaluate_text_with_rubric(
            session,
            text=current_text,
            template_id=body.template_id,
            swarm_id=swarm_id,
            task_id=body.task_id,
        )
        score = _score_from_evaluation(evaluation)
        passed = _turn_passed(evaluation=evaluation, min_score=min_score)
        feedback = str(evaluation.get("feedback") or evaluation.get("reasoning") or "").strip()
        iterations.append(
            ClosedReviewLoopTurnOut(
                turn=turn,
                score=round(score, 4),
                is_valid=bool(evaluation.get("is_valid")),
                passed=passed,
                feedback=feedback[:2000],
            ),
        )
        if passed:
            _logger.info(
                "closed_review_loop.passed",
                agent_id="closed_review_loop",
                swarm_id=swarm_id,
                task_id=body.task_id or "",
                turn=turn,
                score=score,
            )
            return ClosedReviewLoopResultOut(
                ok=True,
                passed=True,
                turns_used=turn,
                max_turns=max_turns,
                min_score=min_score,
                min_score_label=f"{min_score * 5:.1f}/5",
                template_id=template.id,
                template_name=template.name,
                initial_text=body.text.strip(),
                final_text=current_text,
                iterations=iterations,
                message=f"Rubric pass on turn {turn} (score {score:.0%}).",
            )

        if turn >= max_turns:
            break

        current_text = await _revise_text_from_feedback(
            session,
            text=current_text,
            feedback=feedback or "Improve clarity, specificity, and rubric must_satisfy gates.",
            template_name=template.name,
            tenant_id=tenant_id,
            task_id=body.task_id,
        )

    last = iterations[-1] if iterations else None
    _logger.info(
        "closed_review_loop.exhausted",
        agent_id="closed_review_loop",
        swarm_id=swarm_id,
        task_id=body.task_id or "",
        turns=len(iterations),
        last_score=last.score if last else 0.0,
    )
    return ClosedReviewLoopResultOut(
        ok=True,
        passed=False,
        turns_used=len(iterations),
        max_turns=max_turns,
        min_score=min_score,
        min_score_label=f"{min_score * 5:.1f}/5",
        template_id=template.id,
        template_name=template.name,
        initial_text=body.text.strip(),
        final_text=current_text,
        iterations=iterations,
        message=(
            f"Max turns ({max_turns}) reached without pass. "
            f"Last score {last.score:.0%} vs min {min_score:.0%}."
            if last
            else "No evaluation turns completed."
        ),
    )


__all__ = [
    "ClosedReviewLoopResultOut",
    "ClosedReviewLoopRunIn",
    "ClosedReviewLoopTurnOut",
    "run_closed_review_loop",
]
