"""Unit tests for objective and guardrail auditing."""

from __future__ import annotations

from scripts.objective_guardrail_auditor import AuditObjective, audit_objective, render_audit_report


def test_audit_objective_flags_live_pricing_without_approval() -> None:
    audit = audit_objective(
        AuditObjective(
            name="autonomous pricing bot",
            objective="maximize profit by changing prices live above competitor average",
            guardrails=["keep margin high"],
        ),
    )

    assert audit.verdict == "blocked"
    assert "live_action_without_approval" in audit.risks
    assert "supracompetitive_pricing_pattern" in audit.risks
    assert "missing_approval_gate" in audit.risks


def test_render_audit_report_includes_safe_rewrite_and_file_based_record() -> None:
    audit = audit_objective(
        AuditObjective(
            name="gumroad launch advisor",
            objective="recommend a sustainable Gumroad launch price after simulation",
            guardrails=["approval gate before live changes", "preserve customer trust"],
        ),
    )
    report = render_audit_report([audit])

    assert "# Objective Guardrail Audit" in report
    assert "gumroad launch advisor" in report
    assert "verdict: review" in report
    assert "Safe objective rewrite" in report
    assert "No live actions are permitted" in report
