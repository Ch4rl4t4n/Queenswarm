"""Planner coverage for parallel batch boundaries derived from breaker JSON."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.sub_swarm.plan import plan_execution_batches


def _mock_step(order: int) -> MagicMock:
    """Return a ORM-shaped stand-in carrying ``step_order``."""

    step = MagicMock()
    step.step_order = order
    step.id = MagicMock()
    return step


def test_plan_serializes_without_parallel_groups() -> None:
    """Absent ``parallelizable_groups`` collapses to sequential singleton batches."""

    steps = [_mock_step(1), _mock_step(2), _mock_step(3)]
    batches = plan_execution_batches(ordered_steps=steps, parallel_groups=[])
    flattened = [[int(s.step_order) for s in batch] for batch in batches]
    assert flattened == [[1], [2], [3]]


def test_plan_merges_declared_parallel_lane() -> None:
    """Breaker orders that share a lane should share the same hive batch."""

    steps = [_mock_step(1), _mock_step(2), _mock_step(3), _mock_step(4)]
    batches = plan_execution_batches(ordered_steps=steps, parallel_groups=[[2, 3]])
    flattened = [[int(s.step_order) for s in batch] for batch in batches]
    assert flattened == [[1], [2, 3], [4]]


def test_plan_splits_parallel_lane_when_gap_must_run_first() -> None:
    """Non-parallel intermediate orders block bundling until they finish."""

    steps = [_mock_step(5), _mock_step(6), _mock_step(7)]
    batches = plan_execution_batches(ordered_steps=steps, parallel_groups=[[5, 7]])
    flattened = [[int(s.step_order) for s in batch] for batch in batches]
    assert flattened == [[5], [6], [7]]


def test_plan_rejects_duplicate_orders() -> None:
    """Malformed ORM loads should raise before LangGraph execution."""

    duplicates = [_mock_step(1), _mock_step(1)]
    with pytest.raises(ValueError, match="duplicate workflow step_order"):
        plan_execution_batches(ordered_steps=duplicates, parallel_groups=[])
