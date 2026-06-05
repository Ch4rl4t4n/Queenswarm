"""Unit tests for Eval-as-a-Service."""

from __future__ import annotations

import pytest

from app.application.services.harness_eval_service import HarnessEvalRequest, run_harness_eval

_VALID_MD = (
    "---\nname: test-workflow\ndescription: Test harness eval\n---\n\n"
    "# Test Workflow\n\nWhen to use: weekly ops.\n\n"
    "1. Research context\n2. Draft output\n3. Simulate before publish\n"
)


@pytest.mark.asyncio
async def test_run_harness_eval_when_valid_md_then_passes_heuristic() -> None:
    result = await run_harness_eval(
        HarnessEvalRequest(workflow_markdown=_VALID_MD, title="Test Workflow", run_llm_critic=False),
    )
    assert result.skill_valid is True
    assert "Tier:" in result.eval_report_md
    assert result.recommended_gumroad_price_eur_cents in {1900, 2900}


@pytest.mark.asyncio
async def test_run_harness_eval_when_invalid_structure_then_fails() -> None:
    bad_md = "x" * 50  # passes min length but not valid SKILL structure
    result = await run_harness_eval(
        HarnessEvalRequest(workflow_markdown=bad_md, title="Bad", run_llm_critic=False),
    )
    assert result.passed is False
    assert len(result.issues) > 0


@pytest.mark.asyncio
async def test_run_harness_eval_when_llm_critic_without_session_then_raises() -> None:
    with pytest.raises(ValueError, match="eval_session_required"):
        await run_harness_eval(
            HarnessEvalRequest(workflow_markdown=_VALID_MD, title="Test", run_llm_critic=True),
        )


def test_validate_factory_critic_model_rejects_unknown_slug() -> None:
    from app.application.services.factory_llm_readiness_service import validate_factory_critic_model

    with pytest.raises(ValueError, match="unsupported_critic_model"):
        validate_factory_critic_model("unknown/vendor/model")
