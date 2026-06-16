"""Unit coverage for workflow decomposition validators."""

from __future__ import annotations

from app.workflows.validators import WorkflowValidator


def test_validate_decomposition_rejects_non_list_steps() -> None:
    ok, errs = WorkflowValidator.validate_decomposition({"steps": "nope"})
    assert ok is False
    assert any("steps" in e for e in errs)


def test_validate_decomposition_rejects_step_count_out_of_range() -> None:
    payload = {
        "steps": [
            {
                "order": 1,
                "description": "First valid step",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {"risks": [], "mitigations": [], "stop_conditions": []},
                "evaluation_criteria": {"must_satisfy": [], "measurable_signals": {}},
            },
            {
                "order": 2,
                "description": "Second valid step",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {"risks": [], "mitigations": [], "stop_conditions": []},
                "evaluation_criteria": {"must_satisfy": [], "measurable_signals": {}},
            },
        ],
    }
    ok, errs = WorkflowValidator.validate_decomposition(payload)
    assert ok is False
    assert any("3-7 steps" in e for e in errs)


def test_validate_decomposition_rejects_non_object_step() -> None:
    payload = {"steps": ["bad", {}, {}]}
    ok, errs = WorkflowValidator.validate_decomposition(payload)
    assert ok is False
    assert any("Step 0 must be an object" in e for e in errs)


def test_validate_decomposition_rejects_short_description() -> None:
    payload = {
        "steps": [
            {
                "order": 1,
                "description": "x",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {"risks": [], "mitigations": [], "stop_conditions": []},
                "evaluation_criteria": {"must_satisfy": [], "measurable_signals": {}},
            },
            {
                "order": 2,
                "description": "Second valid step",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {"risks": [], "mitigations": [], "stop_conditions": []},
                "evaluation_criteria": {"must_satisfy": [], "measurable_signals": {}},
            },
            {
                "order": 3,
                "description": "Third valid step",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {"risks": [], "mitigations": [], "stop_conditions": []},
                "evaluation_criteria": {"must_satisfy": [], "measurable_signals": {}},
            },
        ],
    }
    ok, errs = WorkflowValidator.validate_decomposition(payload)
    assert ok is False
    assert any("two tokens" in e for e in errs)


def test_validate_decomposition_requires_guardrail_subkeys() -> None:
    payload = {
        "steps": [
            {
                "order": 1,
                "description": "First valid step",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {"risks": []},
                "evaluation_criteria": {"must_satisfy": [], "measurable_signals": {}},
            },
            {
                "order": 2,
                "description": "Second valid step",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {"risks": [], "mitigations": [], "stop_conditions": []},
                "evaluation_criteria": {"must_satisfy": [], "measurable_signals": {}},
            },
            {
                "order": 3,
                "description": "Third valid step",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {"risks": [], "mitigations": [], "stop_conditions": []},
                "evaluation_criteria": {"must_satisfy": [], "measurable_signals": {}},
            },
        ],
    }
    ok, errs = WorkflowValidator.validate_decomposition(payload)
    assert ok is False
    assert any("guardrails missing" in e for e in errs)


def test_validate_decomposition_requires_evaluation_subkeys() -> None:
    payload = {
        "steps": [
            {
                "order": 1,
                "description": "First valid step",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {"risks": [], "mitigations": [], "stop_conditions": []},
                "evaluation_criteria": {"must_satisfy": []},
            },
            {
                "order": 2,
                "description": "Second valid step",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {"risks": [], "mitigations": [], "stop_conditions": []},
                "evaluation_criteria": {"must_satisfy": [], "measurable_signals": {}},
            },
            {
                "order": 3,
                "description": "Third valid step",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {"risks": [], "mitigations": [], "stop_conditions": []},
                "evaluation_criteria": {"must_satisfy": [], "measurable_signals": {}},
            },
        ],
    }
    ok, errs = WorkflowValidator.validate_decomposition(payload)
    assert ok is False
    assert any("evaluation_criteria missing" in e for e in errs)


def test_validate_step_result_truthy_for_non_empty_dict() -> None:
    assert WorkflowValidator.validate_step_result(step={}, result={"ok": True}) is True
    assert WorkflowValidator.validate_step_result(step={}, result={}) is False
