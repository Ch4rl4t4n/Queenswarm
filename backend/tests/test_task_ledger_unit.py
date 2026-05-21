"""Unit tests for backlog persistence helpers (no database)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.enums import TaskStatus, TaskType
from app.models.task import Task
from app.services.task_ledger import (
    TaskUpsertViolationError,
    apply_task_updates,
    create_task_record,
    fetch_task,
    iter_recent_tasks,
    validate_task_edges,
)


@pytest.mark.asyncio
async def test_validate_task_edges_raises_when_swarm_missing() -> None:
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    sid = uuid.uuid4()
    with pytest.raises(TaskUpsertViolationError, match="swarm_id"):
        await validate_task_edges(session, swarm_id=sid, workflow_id=None, parent_task_id=None)


@pytest.mark.asyncio
async def test_validate_task_edges_passes_when_edges_none() -> None:
    session = AsyncMock()
    await validate_task_edges(session, swarm_id=None, workflow_id=None, parent_task_id=None)
    session.get.assert_not_called()


@pytest.mark.asyncio
async def test_create_task_record_flushes_pending_row() -> None:
    session = AsyncMock()
    session.get = AsyncMock(return_value=object())  # any non-None FK target
    session.add = MagicMock()
    session.flush = AsyncMock()

    row = await create_task_record(
        session,
        title="Hive crawl",
        task_type_value=TaskType.SCRAPE,
        priority=7,
        payload={"url": "https://queenswarm.love"},
        swarm_id=uuid.uuid4(),
        workflow_id=None,
        parent_task_id=None,
    )
    assert isinstance(row, Task)
    assert row.status == TaskStatus.PENDING
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_validate_task_edges_raises_when_workflow_missing() -> None:
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    wid = uuid.uuid4()
    with pytest.raises(TaskUpsertViolationError, match="workflow_id"):
        await validate_task_edges(session, swarm_id=None, workflow_id=wid, parent_task_id=None)


@pytest.mark.asyncio
async def test_validate_task_edges_raises_when_parent_missing() -> None:
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    pid = uuid.uuid4()
    with pytest.raises(TaskUpsertViolationError, match="parent_task_id"):
        await validate_task_edges(session, swarm_id=None, workflow_id=None, parent_task_id=pid)


@pytest.mark.asyncio
async def test_fetch_task_returns_row() -> None:
    task_id = uuid.uuid4()
    row = Task(title="x", task_type=TaskType.REPORT, priority=1, payload={})
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)

    found = await fetch_task(session, task_id)

    assert found is row
    session.get.assert_awaited_once_with(Task, task_id)


@pytest.mark.asyncio
async def test_iter_recent_tasks_clamps_limit_and_returns_rows() -> None:
    task = MagicMock()
    scalar_result = MagicMock()
    scalar_result.all.return_value = [task]
    executed = MagicMock()
    executed.scalars.return_value = scalar_result
    session = AsyncMock()
    session.execute = AsyncMock(return_value=executed)

    rows = await iter_recent_tasks(
        session,
        swarm_id=uuid.uuid4(),
        status=TaskStatus.PENDING,
        limit=999,
    )

    assert rows == [task]
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_apply_task_updates_merges_fields() -> None:
    session = AsyncMock()
    session.flush = AsyncMock()
    row = Task(title="t", task_type=TaskType.REPORT, priority=1, payload={})
    row.status = TaskStatus.PENDING

    await apply_task_updates(
        session,
        row,
        status=TaskStatus.COMPLETED,
        result={"ok": True},
        error_msg=None,
    )
    assert row.status == TaskStatus.COMPLETED
    assert row.result == {"ok": True}
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_apply_task_updates_sets_error_msg() -> None:
    session = AsyncMock()
    session.flush = AsyncMock()
    row = Task(title="t", task_type=TaskType.REPORT, priority=1, payload={})

    await apply_task_updates(session, row, status=None, result=None, error_msg="timeout")

    assert row.error_msg == "timeout"
    session.flush.assert_awaited_once()
