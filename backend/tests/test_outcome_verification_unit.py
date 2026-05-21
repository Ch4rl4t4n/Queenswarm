"""Rules for sanitizing swarm workflow payloads prior to dashboards."""

from __future__ import annotations

import pytest

from app.services.outcome_verification import (
    assess_internal_step_outputs,
    build_operator_step_summaries,
    max_simulator_confidence_fraction,
    maybe_attach_internal_echo,
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


def test_max_simulator_confidence_fraction_picks_best() -> None:
    internals = [
        {
            "order": 1,
            "status": "completed",
            "agent_role": "simulator",
            "result": {"confidence_pct": 55},
        },
        {
            "order": 2,
            "status": "completed",
            "agent_role": "simulator",
            "result": {"confidence": 0.92},
        },
    ]
    assert max_simulator_confidence_fraction(internals) == pytest.approx(0.92)


def test_max_simulator_confidence_fraction_none_when_missing() -> None:
    assert max_simulator_confidence_fraction([]) is None


def test_assess_notes_when_verification_not_passed() -> None:
    internals = [
        {
            "order": 1,
            "status": "completed",
            "agent_role": "simulator",
            "result": {"verification_passed": False, "confidence": 0.99},
        },
    ]
    passed, notes = assess_internal_step_outputs(internals, threshold=0.7)
    assert passed is False
    assert any("did not acknowledge" in n for n in notes)


def test_maybe_attach_internal_echo_respects_flag() -> None:
    rows = [{"order": 1}]
    assert maybe_attach_internal_echo(rows, expose_raw=False) == []
    assert maybe_attach_internal_echo(rows, expose_raw=True) == rows


def test_build_operator_step_summaries_verified_exposes_raw() -> None:
    internals = [{"order": 1, "result": {"secret": True}}]
    out = build_operator_step_summaries(internals, verified=True, expose_raw=False)
    assert out[0]["result"]["secret"] is True
