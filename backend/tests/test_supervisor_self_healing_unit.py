"""Unit tests for supervisor self-healing and autonomy helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.services.supervisor.runtime import (
    build_needs_input_request,
    detect_step_issues,
    evaluate_meta_reasoning,
    is_approval_required,
    run_self_healing_cycle,
)
from app.core.config import settings


def test_detect_step_issues_when_context_missing_then_flags_missing_context() -> None:
    """Missing retrieval context and weak output are detected for retry."""

    issues = detect_step_issues(
        retrieval_contract="default_v2",
        retrieval_sections=[],
        selected_skills=["context"],
        output_text="too short",
    )
    assert "missing_context" in issues
    assert "bad_output" in issues


def test_build_needs_input_request_when_issues_present_then_returns_precise_payload() -> None:
    """Needs-input payload includes explicit asks and alternatives."""

    payload = build_needs_input_request(
        role="researcher",
        goal="Evaluate customer migration policy",
        issues=["missing_context"],
        alternatives=["Request expanded retrieval bundle."],
    )
    assert payload["requested_by"] == "researcher"
    assert "required_user_input" in payload
    assert payload["alternatives"]


def test_detect_step_issues_when_long_llm_output_mentions_error_then_not_bad_output() -> None:
    """Long verified LLM reports must not fail self-heal on incidental 'error' tokens."""

    issues = detect_step_issues(
        retrieval_contract="",
        retrieval_sections=["policy"],
        selected_skills=["context"],
        output_text=(
            "## Finding 1\n"
            "- claim: Operators should monitor rate-limit errors in RSS feeds.\n"
            "This is a detailed verified report with enough content to pass length checks "
            "and should not be rejected because the word error appears in context."
        ),
    )
    assert "bad_output" not in issues


def test_detect_step_issues_when_skill_factory_critic_reject_then_not_bad_output() -> None:
    """Factory critic reject verdict is a valid terminal gate result, not a retry loop."""

    issues = detect_step_issues(
        retrieval_contract="",
        retrieval_sections=["coder draft"],
        selected_skills=["self-review-loop"],
        output_text=(
            "Critic verdict: REJECT\n\n"
            "---\n"
            "Tool highlights:\n"
            "- wikipedia: transient connector error"
        ),
        role="critic",
        context_summary={"skill_factory": True},
    )

    assert "bad_output" not in issues


def test_is_approval_required_when_critical_goal_then_true() -> None:
    """Critical action keywords trigger approval workflow."""

    required, reason = is_approval_required(
        goal="Delete production billing secrets after rotation",
        toolset=["edit_code"],
        context_summary={},
    )
    assert required is True
    assert "keyword" in reason.lower()


def test_is_approval_required_when_social_intel_drop_verdict_phrase_then_false() -> None:
    """Social intel Grok gate prose must not false-positive on keyword 'drop'."""

    raw = (
        "Social intel forager 'X Intel': drop verdict=false, tag hivemind-candidate. "
        "Simulate-first only."
    )
    required, reason = is_approval_required(
        goal=f"=== MISSION ===\nbilling admin\n=== END CONTEXT ===\n{raw}",
        toolset=[],
        context_summary={"raw_goal": raw, "approval_required": True},
    )
    assert required is False, reason


def test_evaluate_meta_reasoning_when_issues_present_then_score_drops() -> None:
    """Meta-reasoning score reflects unresolved issues and adaptation guidance."""

    out = evaluate_meta_reasoning(
        role="critic",
        goal="Audit production rotation path",
        retrieval_sections=[],
        selected_skills=[],
        issues=["missing_context", "bad_output"],
        alternatives=["Expand retrieval", "Tighten checklist"],
        attempts=2,
        resolved=False,
    )
    assert out["strategy_score"] < 0.8
    assert out["recommended_shift"] == "expand_retrieval_contract"


@pytest.mark.asyncio
async def test_run_self_healing_cycle_when_first_attempt_bad_then_self_corrects(monkeypatch) -> None:
    """Self-healing retries once and succeeds after correction."""

    monkeypatch.setattr(settings, "supervisor_self_heal_max_attempts", 2)
    outputs = ["bad", "This is a valid corrected output with enough details to pass."]
    state = SimpleNamespace(index=0, adjusted=False)

    async def _execute_attempt(_attempt: int, _hint: str | None) -> str:
        out = outputs[state.index]
        state.index += 1
        return out

    async def _adjustment(_attempt: int, _issues: list[str]) -> None:
        state.adjusted = True

    result = await run_self_healing_cycle(
        role="coder",
        goal="Stabilize execution path",
        retrieval_contract="",
        retrieval_sections=[],
        selected_skills=["self-review-loop"],
        execute_attempt=_execute_attempt,
        retry_adjustment=_adjustment,
    )
    assert result.resolved is True
    assert result.attempts == 2
    assert state.adjusted is True
    assert len(result.reflections) == 2
    assert "what_went_well" in result.reflections[-1]
    assert "what_to_improve" in result.reflections[-1]
    assert "strategy_score" in result.meta_reasoning


@pytest.mark.asyncio
async def test_run_self_healing_cycle_when_all_attempts_fail_then_requests_input(monkeypatch) -> None:
    """Unresolved self-healing returns needs-input payload for operator."""

    monkeypatch.setattr(settings, "supervisor_self_heal_max_attempts", 2)

    async def _execute_attempt(_attempt: int, _hint: str | None) -> str:
        return "error: cannot proceed"

    result = await run_self_healing_cycle(
        role="critic",
        goal="Audit risky operation",
        retrieval_contract="default_v2",
        retrieval_sections=[],
        selected_skills=[],
        execute_attempt=_execute_attempt,
    )
    assert result.resolved is False
    assert result.needs_input_request is not None
    assert "issues" in result.needs_input_request
    assert result.meta_reasoning["resolved"] is False
