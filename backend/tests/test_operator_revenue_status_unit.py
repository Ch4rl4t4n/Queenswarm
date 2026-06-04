"""Unit tests for the operator revenue status runbook."""

from __future__ import annotations

from pathlib import Path

from scripts.operator_revenue_status import RevenueStatusInputs, render_revenue_status


def test_render_revenue_status_summarizes_core_reports(tmp_path: Path) -> None:
    queue = tmp_path / "UPLOAD_QUEUE.md"
    scorecard = tmp_path / "GUMROAD_SCORECARD.md"
    simulation = tmp_path / "GUMROAD_LAUNCH_STRATEGY.md"
    audit = tmp_path / "GUMROAD_OBJECTIVE_AUDIT.md"
    model_eval = tmp_path / "MODEL_EVAL_REPORT.md"
    queue.write_text(
        "\n".join(
            [
                "# Gumroad Ready Upload Queue",
                "",
                "1. `first-product` (content_pack, score 115)",
                "   - Price: EUR 19.00",
            ],
        ),
        encoding="utf-8",
    )
    scorecard.write_text("# Gumroad Product Scorecard\n\nReady: **16/16**\n", encoding="utf-8")
    simulation.write_text(
        "# Business Strategy Simulation\n\nStart with a trust-building offer around EUR 19.\n",
        encoding="utf-8",
    )
    audit.write_text("# Objective Guardrail Audit\n\n- verdict: review\n", encoding="utf-8")
    model_eval.write_text(
        "# Model Evaluation Swarm\n\n- `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`\n",
        encoding="utf-8",
    )

    report = render_revenue_status(
        RevenueStatusInputs(
            upload_queue=queue,
            scorecard=scorecard,
            business_simulation=simulation,
            objective_audit=audit,
            model_eval=model_eval,
        ),
    )

    assert "# Queenswarm Revenue Operator Status" in report
    assert "Ready: **16/16**" in report
    assert "`first-product`" in report
    assert "verdict: review" in report
    assert "trust-building offer" in report
    assert "Nemotron" in report
    assert "Upload product #1" in report


def test_render_revenue_status_marks_missing_reports(tmp_path: Path) -> None:
    report = render_revenue_status(
        RevenueStatusInputs(
            upload_queue=tmp_path / "missing-queue.md",
            scorecard=tmp_path / "missing-scorecard.md",
            business_simulation=tmp_path / "missing-simulation.md",
            objective_audit=tmp_path / "missing-audit.md",
            model_eval=tmp_path / "missing-model-eval.md",
        ),
    )

    assert "missing" in report
    assert "Regenerate operator reports" in report
