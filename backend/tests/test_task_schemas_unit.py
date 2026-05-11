"""Pydantic coverage for task backlog HTTP contracts."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.models.enums import TaskStatus, TaskType
from app.schemas.task import TaskCreateRequest, TaskPatchRequest


def test_task_create_request_accepts_minimal_payload() -> None:
    body = TaskCreateRequest(title="Scout https://example.com", task_type=TaskType.SCRAPE)
    assert body.priority == 5
    assert body.payload == {}
    assert body.swarm_id is None


def test_task_create_request_rejects_short_title() -> None:
    with pytest.raises(ValidationError):
        TaskCreateRequest(title="x", task_type=TaskType.EVALUATE)


def test_task_patch_request_allows_partial() -> None:
    patch = TaskPatchRequest(status=TaskStatus.RUNNING)
    assert patch.result is None
    assert patch.error_msg is None


def test_task_create_request_payload_roundtrip() -> None:
    wid = uuid.uuid4()
    body = TaskCreateRequest(
        title="Simulate pricing delta",
        task_type=TaskType.SIMULATE,
        priority=3,
        payload={"symbol": "QS"},
        workflow_id=wid,
    )
    assert body.workflow_id == wid
