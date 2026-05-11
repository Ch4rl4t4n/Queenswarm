"""Unit coverage for Auto Workflow Breaker parsing + schema validation."""

from __future__ import annotations

import json
import uuid

import pytest
from pydantic import ValidationError

from app.schemas.workflow_breaker import BreakerDecomposition, BreakerStepDraft
from app.services.workflow_breaker import parsing as parsing_module


def test_extract_json_object_strips_fenced_payload() -> None:
    """Fence trimming should still yield a dict for downstream Pydantic."""

    inner = {
        "rationale": "detailed rationale explaining guardrails and sync cadence",
        "parallelizable_groups": [[2, 3]],
        "estimated_duration_sec": 300,
        "steps": [
            {
                "order": 1,
                "description": "Scout social sentiment",
                "agent_role": "scraper",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {
                    "risks": ["scraping blocks"],
                    "mitigations": ["rotate user agent"],
                    "stop_conditions": [],
                },
                "evaluation_criteria": {
                    "must_satisfy": ["source list"],
                    "measurable_signals": {},
                },
            },
            {
                "order": 2,
                "description": "Evaluate factual claims",
                "agent_role": "evaluator",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {
                    "risks": [],
                    "mitigations": [],
                    "stop_conditions": [],
                },
                "evaluation_criteria": {
                    "must_satisfy": [],
                    "measurable_signals": {},
                },
            },
            {
                "order": 3,
                "description": "Simulate engagement outcomes",
                "agent_role": "simulator",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {
                    "risks": [],
                    "mitigations": [],
                    "stop_conditions": [],
                },
                "evaluation_criteria": {
                    "must_satisfy": [],
                    "measurable_signals": {},
                },
            },
        ],
    }
    raw = f"```json\n{json.dumps(inner)}\n```"
    blob = parsing_module.extract_breaker_json(raw)
    parsed = BreakerDecomposition.model_validate(blob)
    assert parsed.parallelizable_groups == [[2, 3]]


def test_breaker_decomposition_validates_parallel_groups() -> None:
    """Parallel groups must reference real step order indices."""

    payload = {
        "rationale": "long enough rationale string",
        "parallelizable_groups": [[9]],
        "steps": [
            {
                "order": 1,
                "description": "Simulate portfolio drawdown",
                "agent_role": "simulator",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {
                    "risks": ["model drift"],
                    "mitigations": ["use sandbox"],
                    "stop_conditions": ["loss > 15%"],
                },
                "evaluation_criteria": {
                    "must_satisfy": ["pass docker sim"],
                    "measurable_signals": {"drawdown": "<= 0.15"},
                },
            },
            {
                "order": 2,
                "description": "Report findings to hive",
                "agent_role": "reporter",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {
                    "risks": ["misinformation"],
                    "mitigations": ["human review"],
                    "stop_conditions": ["sim fail"],
                },
                "evaluation_criteria": {
                    "must_satisfy": ["facts cited"],
                    "measurable_signals": {},
                },
            },
            {
                "order": 3,
                "description": "Queue social post draft",
                "agent_role": "social_poster",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {
                    "risks": [],
                    "mitigations": [],
                    "stop_conditions": [],
                },
                "evaluation_criteria": {
                    "must_satisfy": [],
                    "measurable_signals": {},
                },
            },
        ],
    }

    with pytest.raises(ValidationError):
        BreakerDecomposition.model_validate(payload)

    payload["parallelizable_groups"] = [[2, 3]]
    parsed = BreakerDecomposition.model_validate(payload)
    assert len(parsed.steps) == 3


def test_json_snippet_embedded_in_prose() -> None:
    """Extract the first balanced object when vendors add chatter."""

    chatter = (
        "Sure! Here is JSON\n"
        + json.dumps(
            {
                "rationale": "long enough rationale text",
                "parallelizable_groups": [],
                "estimated_duration_sec": 120,
                "steps": [
                    {
                        "order": 1,
                        "description": "Scout market signals",
                        "agent_role": "scraper",
                        "input_schema": {},
                        "output_schema": {},
                        "guardrails": {
                            "risks": ["rate limit"],
                            "mitigations": ["cache"],
                            "stop_conditions": [],
                        },
                        "evaluation_criteria": {
                            "must_satisfy": ["freshness < 5m"],
                            "measurable_signals": {},
                        },
                    },
                    {
                        "order": 2,
                        "description": "Evaluate source quality",
                        "agent_role": "evaluator",
                        "input_schema": {},
                        "output_schema": {},
                        "guardrails": {
                            "risks": [],
                            "mitigations": [],
                            "stop_conditions": [],
                        },
                        "evaluation_criteria": {
                            "must_satisfy": [],
                            "measurable_signals": {},
                        },
                    },
                    {
                        "order": 3,
                        "description": "Simulate trade impact",
                        "agent_role": "simulator",
                        "input_schema": {},
                        "output_schema": {},
                        "guardrails": {
                            "risks": [],
                            "mitigations": [],
                            "stop_conditions": [],
                        },
                        "evaluation_criteria": {
                            "must_satisfy": [],
                            "measurable_signals": {},
                        },
                    },
                ],
            },
        )
        + "\nHope this helps."
    )
    blob = parsing_module.extract_breaker_json(chatter)
    model = BreakerDecomposition.model_validate(blob)
    assert model.estimated_duration_sec == 120


def test_step_description_requires_multiple_tokens() -> None:
    """Breaker steps should never collapse into a single ambiguous token."""

    with pytest.raises(ValidationError):
        BreakerStepDraft(
            order=1,
            description="short",
            agent_role="scraper",
            input_schema={},
            output_schema={},
            guardrails={"risks": [], "mitigations": [], "stop_conditions": []},
            evaluation_criteria={"must_satisfy": [], "measurable_signals": {}},
        )


def test_workflow_validator_rejects_vague_verbs() -> None:
    """Blacklist should catch analyse/process phrasing before strict Pydantic."""

    from app.workflows.validators import WorkflowValidator

    payload = {
        "rationale": "long enough rationale text",
        "parallelizable_groups": [],
        "estimated_duration_sec": 120,
        "steps": [
            {
                "order": 1,
                "description": "Analyze the market carefully",
                "agent_role": "scraper",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {"risks": [], "mitigations": [], "stop_conditions": []},
                "evaluation_criteria": {"must_satisfy": [], "measurable_signals": {}},
            },
            {
                "order": 2,
                "description": "Second valid step description",
                "agent_role": "evaluator",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {"risks": [], "mitigations": [], "stop_conditions": []},
                "evaluation_criteria": {"must_satisfy": [], "measurable_signals": {}},
            },
            {
                "order": 3,
                "description": "Third valid step description",
                "agent_role": "simulator",
                "input_schema": {},
                "output_schema": {},
                "guardrails": {"risks": [], "mitigations": [], "stop_conditions": []},
                "evaluation_criteria": {"must_satisfy": [], "measurable_signals": {}},
            },
        ],
    }
    ok, errs = WorkflowValidator.validate_decomposition(payload)
    assert ok is False
    assert any("vague" in e.lower() for e in errs)


def test_decompose_request_accepts_uuid_strings() -> None:
    """Recipe UUID hints should marshal cleanly inside request bodies."""

    from app.schemas.workflow_breaker import DecomposeWorkflowRequest

    rid = uuid.uuid4()
    model = DecomposeWorkflowRequest.model_validate(
        {
            "task_text": "Coordinate swarm readiness report for operators",
            "matching_recipe_id": str(rid),
        },
    )
    assert model.matching_recipe_id == rid
