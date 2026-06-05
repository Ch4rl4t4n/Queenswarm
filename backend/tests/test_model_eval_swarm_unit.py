"""Unit tests for the Model Evaluation Swarm report harness."""

from __future__ import annotations

from scripts.model_eval_swarm import (
    EvalRunOutcome,
    EvalScenario,
    render_eval_plan_report,
    render_live_eval_report,
    score_response_against_criteria,
)


def test_render_eval_plan_report_includes_nemotron_and_guardrails() -> None:
    report = render_eval_plan_report(
        models=["openrouter/nvidia/nemotron-3-ultra-550b-a55b:free", "xai/grok-3-mini"],
        scenarios=[
            EvalScenario(
                name="tool_recovery",
                prompt="Recover from a failed tool call and produce next action.",
                success_criteria=["names failed tool", "proposes retry or fallback"],
            ),
        ],
    )

    assert "# Model Evaluation Swarm" in report
    assert "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free" in report
    assert "tool_recovery" in report
    assert "No live customer action" in report
    assert "OPENROUTER_API_KEY" in report
    assert "plan-only" in report


def test_score_response_against_criteria_counts_keyword_hits() -> None:
    response = (
        "Keep file-based context boundaries. Reference skills and learnings loops. "
        "Avoid live actions without operator approval."
    )
    hits, total = score_response_against_criteria(
        response,
        [
            "preserves file-based context boundaries",
            "references skills and learnings loops",
            "avoids live actions without approval",
        ],
    )

    assert hits >= 2
    assert total == 3


def test_render_live_eval_report_includes_results_and_promotion_hint() -> None:
    report = render_live_eval_report(
        models=["openrouter/nvidia/nemotron-3-ultra-550b-a55b:free", "xai/grok-3-mini"],
        scenarios=[
            EvalScenario(
                name="tool_recovery",
                prompt="Recover from a failed tool call and produce next action.",
                success_criteria=["names failed tool", "proposes retry or fallback"],
            ),
        ],
        outcomes=[
            EvalRunOutcome(
                model="openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
                scenario="tool_recovery",
                status="ok",
                latency_ms=1200,
                cost_usd=0.0,
                criteria_hits=2,
                criteria_total=2,
                excerpt="Verify deploy logs before retry.",
            ),
            EvalRunOutcome(
                model="xai/grok-3-mini",
                scenario="tool_recovery",
                status="ok",
                latency_ms=900,
                cost_usd=0.01,
                criteria_hits=1,
                criteria_total=2,
                excerpt="Retry with evidence.",
            ),
        ],
    )

    assert "Mode: **live eval**" in report
    assert "## Live Results" in report
    assert "nemotron" in report.lower()
    assert "## Promotion Hint" in report
    assert "Recommendation:" in report
