"""Unit tests for task snapshot derivation helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.enums import TaskStatus, TaskType
from app.models.task import Task
from app.services.task_presenter import (
    attach_agent_labels,
    build_task_snapshot,
    confidence_from_task_result,
    cost_usd_from_task_result,
    output_format_from_result,
)


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (None, None),
        ("not-a-dict", None),
        ({"confidence_score": "0.5"}, 0.5),
        ({"confidence_score": 2.0}, 0.02),  # >1 treated as pct scale heuristic
        ({"confidence_pct": 75}, 0.75),
        ({"confidence_pct": "oops"}, None),
        ({"confidence_score": "oops"}, None),
        ({"confidence_score": "-1"}, 0.0),
        ({"confidence_pct": "-5"}, 0.0),
        ({}, None),
    ],
)
def test_confidence_from_task_result_handles_edges(
    result: object,
    expected: float | None,
) -> None:
    assert confidence_from_task_result(result) == expected


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (None, None),
        ({}, None),
        ({"cost_usd": "3.14"}, 3.14),
        ({"cost_usd": 2}, 2.0),
        ({"cost_usd": "bad"}, None),
        ("oops", None),
    ],
)
def test_cost_usd_from_task_result(
    result: object,
    expected: float | None,
) -> None:
    assert cost_usd_from_task_result(result) == expected


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (None, None),
        ({}, None),
        ({"format": "JSON"}, "json"),
        ({"format": "  MARKDOWN "}, "markdown"),
        ({"format": ""}, None),
        ({"format": 9}, None),
    ],
)
def test_output_format_from_result(
    result: object,
    expected: str | None,
) -> None:
    assert output_format_from_result(result) == expected


def _make_task(**kwargs: object) -> Task:
    now = datetime.now(tz=UTC)
    payload = kwargs.get("payload", {})
    result = kwargs.get("result")
    agent_id = kwargs.get("agent_id")
    row = Task(
        title=str(kwargs.get("title", "t")),
        task_type=kwargs["task_type"] if "task_type" in kwargs else TaskType.REPORT,
        status=kwargs["status"] if "status" in kwargs else TaskStatus.PENDING,
        payload=payload if isinstance(payload, dict) else {},
        priority=int(kwargs.get("priority", 5)),
        pollen_awarded=float(kwargs.get("pollen_awarded", 0.0)),
    )
    row.id = uuid.uuid4()
    row.created_at = kwargs.get("created_at", now)  # type: ignore[assignment]
    row.updated_at = kwargs.get("updated_at", now)  # type: ignore[assignment]
    row.agent_id = agent_id  # type: ignore[assignment]
    row.result = result  # type: ignore[assignment]
    return row


def test_build_task_snapshot_merges_result_telemetry_and_agent_label() -> None:
    row = _make_task(
        task_type=TaskType.AGENT_RUN,
        status=TaskStatus.COMPLETED,
        result={"confidence_pct": 42, "format": "Markdown", "cost_usd": 9.99},
        agent_id=uuid.uuid4(),
    )
    snap = build_task_snapshot(row, agent_label="ScoutBee")
    assert snap.agent_name == "ScoutBee"
    assert snap.output_format == "markdown"
    assert snap.confidence_score == pytest.approx(0.42)
    assert snap.cost_usd == pytest.approx(9.99)


@pytest.mark.asyncio
async def test_attach_agent_labels_batches_ids() -> None:
    bee = uuid.uuid4()
    a = _make_task(title="one", agent_id=bee)
    b = _make_task(title="two", agent_id=None)

    stmt_result = MagicMock()
    stmt_result.all.return_value = [(bee, "Queen Bee")]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=stmt_result)

    labels = await attach_agent_labels(session, [a, b])
    assert labels == {bee: "Queen Bee"}
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_attach_agent_labels_empty_when_missing_agent_ids() -> None:
    row = _make_task(agent_id=None)
    session = AsyncMock()

    labels = await attach_agent_labels(session, [row])
    assert labels == {}
    session.execute.assert_not_called()
