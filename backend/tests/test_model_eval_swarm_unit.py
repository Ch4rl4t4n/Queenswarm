"""Unit tests for the Model Evaluation Swarm report harness."""

from __future__ import annotations

from scripts.model_eval_swarm import EvalScenario, render_eval_plan_report


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
