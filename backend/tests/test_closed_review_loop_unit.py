"""Unit tests for LOOP1 closed review loop."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.closed_review_loop_service import (
    ClosedReviewLoopRunIn,
    _score_from_evaluation,
    _turn_passed,
    run_closed_review_loop,
)
from app.application.services.loop_guardrails_service import LoopGuardrailsPolicyOut


def test_score_from_evaluation_uses_confidence() -> None:
    assert _score_from_evaluation({"confidence": 0.82, "is_valid": True}) == pytest.approx(0.82)


def test_turn_passed_requires_valid_and_threshold() -> None:
    assert _turn_passed(evaluation={"is_valid": True, "confidence": 0.85, "pass_threshold": 0.8}, min_score=0.8)
    assert not _turn_passed(evaluation={"is_valid": False, "confidence": 0.9}, min_score=0.8)


@pytest.mark.asyncio
async def test_run_closed_review_loop_passes_on_first_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "closed_review_loop_enabled", True)

    session = AsyncMock()
    with patch(
        "app.application.services.closed_review_loop_service.get_loop_guardrails_policy",
        AsyncMock(return_value=LoopGuardrailsPolicyOut(max_turns=5, min_score=0.8)),
    ), patch(
        "app.application.services.closed_review_loop_service.evaluate_text_with_rubric",
        AsyncMock(return_value={"is_valid": True, "confidence": 0.9, "feedback": "Good.", "pass_threshold": 0.75}),
    ):
        result = await run_closed_review_loop(
            session,
            tenant_id=uuid.uuid4(),
            body=ClosedReviewLoopRunIn(text="Strong marketing headline with clear CTA.", template_id="copy-marketing"),
        )

    assert result.passed is True
    assert result.turns_used == 1
    assert len(result.iterations) == 1


@pytest.mark.asyncio
async def test_run_closed_review_loop_self_heals_then_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "closed_review_loop_enabled", True)

    session = AsyncMock()
    evaluations = [
        {"is_valid": False, "confidence": 0.55, "feedback": "CTA too vague.", "pass_threshold": 0.75},
        {"is_valid": True, "confidence": 0.88, "feedback": "Much better.", "pass_threshold": 0.75},
    ]
    with patch(
        "app.application.services.closed_review_loop_service.get_loop_guardrails_policy",
        AsyncMock(return_value=LoopGuardrailsPolicyOut(max_turns=3, min_score=0.75)),
    ), patch(
        "app.application.services.closed_review_loop_service.evaluate_text_with_rubric",
        AsyncMock(side_effect=evaluations),
    ), patch(
        "app.application.services.closed_review_loop_service._revise_text_from_feedback",
        AsyncMock(return_value="Revised headline with explicit Start free trial CTA."),
    ):
        result = await run_closed_review_loop(
            session,
            tenant_id=uuid.uuid4(),
            body=ClosedReviewLoopRunIn(
                text="Generic marketing copy without strong action.",
                template_id="marketing-creative",
            ),
        )

    assert result.passed is True
    assert result.turns_used == 2
    assert result.final_text.startswith("Revised")


@pytest.mark.asyncio
async def test_run_closed_review_loop_exhausts_turns(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "closed_review_loop_enabled", True)

    session = AsyncMock()
    with patch(
        "app.application.services.closed_review_loop_service.get_loop_guardrails_policy",
        AsyncMock(return_value=LoopGuardrailsPolicyOut(max_turns=2, min_score=0.8)),
    ), patch(
        "app.application.services.closed_review_loop_service.evaluate_text_with_rubric",
        AsyncMock(return_value={"is_valid": False, "confidence": 0.4, "feedback": "Weak.", "pass_threshold": 0.75}),
    ), patch(
        "app.application.services.closed_review_loop_service._revise_text_from_feedback",
        AsyncMock(return_value="Still weak revised marketing copy draft."),
    ):
        result = await run_closed_review_loop(
            session,
            tenant_id=uuid.uuid4(),
            body=ClosedReviewLoopRunIn(text="Weak draft marketing copy needs work.", template_id="copy-marketing"),
        )

    assert result.passed is False
    assert result.turns_used == 2
    assert "Max turns" in result.message
