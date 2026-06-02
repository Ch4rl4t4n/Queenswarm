"""Unit tests for mission kanban triage + lineage helpers."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.mission_kanban import (
    MissionKanbanStateError,
    create_mission_triage_task,
    intake_title,
)
from app.infrastructure.persistence.models.enums import TaskStatus, TaskType


def test_intake_title_uses_first_line() -> None:
    """First non-empty line becomes the kanban card title."""

    assert intake_title("Build landing page\nWith SEO") == "Build landing page"


def test_intake_title_fallback_when_too_short() -> None:
    """Very short prompts fall back to a generic title."""

    assert intake_title("ab") == "Mission kanban task"


@pytest.mark.asyncio
async def test_create_mission_triage_task_sets_triage_status() -> None:
    """Triage rows start in TRIAGE status with mission_kanban payload."""

    session = AsyncMock()
    fake_row = MagicMock()
    fake_row.id = uuid.uuid4()
    fake_row.agent_id = None
    fake_row.title = "Launch content week"
    fake_row.task_type = TaskType.AGENT_RUN
    fake_row.status = TaskStatus.TRIAGE
    fake_row.priority = 5
    fake_row.payload = {"mission_kanban": True, "triage": True, "task_text": "Launch content week"}
    fake_row.result = None
    fake_row.swarm_id = None
    fake_row.workflow_id = None
    fake_row.parent_task_id = None
    fake_row.pollen_awarded = 0.0
    fake_row.error_msg = None
    fake_row.created_at = MagicMock()
    fake_row.updated_at = MagicMock()
    fake_row.completed_at = None

    with patch(
        "app.application.services.mission_kanban.create_task_record",
        new_callable=AsyncMock,
        return_value=fake_row,
    ) as create_mock, patch(
        "app.application.services.mission_kanban.attach_agent_labels",
        new_callable=AsyncMock,
        return_value={},
    ), patch(
        "app.application.services.mission_kanban.build_task_snapshot",
        return_value=MagicMock(id=fake_row.id, title=fake_row.title, status=TaskStatus.TRIAGE),
    ):
        result = await create_mission_triage_task(
            session,
            task_text="Launch content week for Queenswarm",
            title=None,
            priority=5,
            swarm_id=None,
        )

    create_mock.assert_awaited_once()
    kwargs = create_mock.await_args.kwargs
    assert kwargs["status"] == TaskStatus.TRIAGE
    assert kwargs["payload"]["triage"] is True
    assert result.task.status == TaskStatus.TRIAGE


@pytest.mark.asyncio
async def test_dispatch_rejects_non_triage_task() -> None:
    """Dispatch only accepts rows still parked in triage."""

    from app.application.services.mission_kanban import dispatch_mission_triage_task

    session = AsyncMock()
    fake_row = MagicMock()
    fake_row.status = TaskStatus.PENDING
    fake_row.payload = {}

    with patch(
        "app.application.services.mission_kanban.fetch_task",
        new_callable=AsyncMock,
        return_value=fake_row,
    ):
        with pytest.raises(MissionKanbanStateError, match="Only triage"):
            await dispatch_mission_triage_task(
                session,
                task_id=uuid.uuid4(),
                swarm_id=uuid.uuid4(),
                start_execution=False,
                defer_to_worker=True,
                execution_payload={},
                requested_by="test",
            )
