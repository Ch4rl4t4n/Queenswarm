"""Rules for sanitizing swarm workflow payloads prior to dashboards."""

from __future__ import annotations

import pytest

from app.services.outcome_verification import (
    assess_internal_step_outputs,
    build_operator_step_summaries,
)


@pytest.mark.parametrize(
    ("internals", "expected"),
    [
        ([], False),
        (
            [
                {
                    "order": 1,
                    "status": "completed",
                    "agent_role": "reporter",
                    "result": {"text": "hello"},
                }
            ],
            False,
        ),
        (
            [
                {
                    "order": 0,
                    "status": "completed",
                    "agent_role": "simulator",
                    "result": {
                        "verification_passed": True,
                        "confidence": 0.95,
                    },
                }
            ],
            True,
        ),
        (
            [
                {
                    "order": 1,
                    "status": "completed",
                    "agent_role": "simulator",
                    "result": {
                        "verification_passed": True,
                        "confidence_pct": 65,
                    },
                }
            ],
            False,
        ),
    ],
)
def test_assess_gate_with_threshold(
    internals: list[dict],
    expected: bool,
) -> None:
    passed, notes = assess_internal_step_outputs(internals, threshold=0.7)
    assert passed is expected
    assert isinstance(notes, list)


def test_operator_projection_redacts_unverified_blob() -> None:
    internals = [
        {
            "step_id": "abc",
            "order": 0,
            "agent_role": "reporter",
            "status": "completed",
            "result": {"answer": "leak_me"},
        }
    ]

    sanitized = build_operator_step_summaries(
        internals,
        verified=False,
        expose_raw=False,
    )
    assert sanitized[0]["result"]["hive_visibility"] == "redacted"
    echoed = build_operator_step_summaries(
        internals,
        verified=False,
        expose_raw=True,
    )
    assert echoed[0]["result"]["answer"] == "leak_me"
