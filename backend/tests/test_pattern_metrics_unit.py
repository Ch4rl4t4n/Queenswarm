"""Unit tests for Prometheus pattern outcome metrics."""

from __future__ import annotations

from prometheus_client import REGISTRY

from app.core.metrics import observe_pattern_session_outcomes


def test_observe_pattern_session_outcomes_increments_counter() -> None:
    """Each pattern/outcome pair increments the Prometheus counter once."""

    before = REGISTRY.get_sample_value(
        "queenswarm_pattern_sessions_total",
        labels={"pattern_id": "planning", "outcome": "success"},
    )
    observe_pattern_session_outcomes(
        pattern_ids=["planning", "reflection", "planning"],
        outcome="success",
    )
    after = REGISTRY.get_sample_value(
        "queenswarm_pattern_sessions_total",
        labels={"pattern_id": "planning", "outcome": "success"},
    )
    assert after == (before or 0) + 1


def test_observe_pattern_session_outcomes_ignores_unknown_outcome() -> None:
    """Non-terminal outcomes must not emit metrics."""

    before = REGISTRY.get_sample_value(
        "queenswarm_pattern_sessions_total",
        labels={"pattern_id": "rag", "outcome": "success"},
    )
    observe_pattern_session_outcomes(pattern_ids=["rag"], outcome="running")
    after = REGISTRY.get_sample_value(
        "queenswarm_pattern_sessions_total",
        labels={"pattern_id": "rag", "outcome": "success"},
    )
    assert after == before
