"""Unit tests for tracer bullet → Kanban slice materialization."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.tracer_bullet_kanban import (
    TracerBulletKanbanDisabledError,
    TracerBulletKanbanNotFoundError,
    slice_workflow_to_kanban,
    task_type_for_agent_role,
)
from app.infrastructure.persistence.models.enums import AgentRole, TaskType


def test_task_type_for_agent_role_maps_scraper() -> None:
    """Scraper steps route to scrape backlog lane."""

    assert task_type_for_agent_role(AgentRole.SCRAPER) is TaskType.SCRAPE


def test_task_type_for_agent_role_fallback() -> None:
    """Unknown roles still produce a routable backlog type."""

    assert task_type_for_agent_role(AgentRole.MARKETER) is TaskType.AGENT_RUN


@pytest.mark.asyncio
async def test_slice_workflow_raises_when_feature_disabled() -> None:
    """Disabled flag blocks slice creation."""

    session = AsyncMock()
    with patch(
        "app.application.services.tracer_bullet_kanban.settings.tracer_bullet_kanban_enabled",
        False,
    ):
        with pytest.raises(TracerBulletKanbanDisabledError):
            await slice_workflow_to_kanban(session, workflow_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_slice_workflow_raises_when_workflow_missing() -> None:
    """Missing workflow surfaces not-found error."""

    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    with patch(
        "app.application.services.tracer_bullet_kanban.settings.tracer_bullet_kanban_enabled",
        True,
    ):
        with pytest.raises(TracerBulletKanbanNotFoundError, match="not found"):
            await slice_workflow_to_kanban(session, workflow_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_slice_workflow_materializes_parent_and_children() -> None:
    """Happy path creates one parent and one child per workflow step."""

    workflow_id = uuid.uuid4()
    step_id = uuid.uuid4()
    step = MagicMock()
    step.id = step_id
    step.step_order = 1
    step.description = "Scrape competitor pricing"
    step.agent_role = AgentRole.SCRAPER

    workflow = MagicMock()
    workflow.id = workflow_id
    workflow.original_task_text = "Analyze competitor pricing landscape"
    workflow.steps = [step]

    session = AsyncMock()
    session.scalar = AsyncMock(return_value=workflow)
    session.get = AsyncMock(return_value=None)

    scalar_for_swarm = MagicMock()
    scalar_for_swarm.limit = MagicMock(return_value=scalar_for_swarm)
    scalar_for_swarm.scalar = AsyncMock(return_value=None)

    parent_id = uuid.uuid4()
    child_id = uuid.uuid4()
    parent_row = MagicMock()
    parent_row.id = parent_id
    parent_row.agent_id = None
    parent_row.payload = {}
    parent_row.swarm_id = None
    child_row = MagicMock()
    child_row.id = child_id
    child_row.agent_id = None

    created: list[MagicMock] = []

    async def _fake_create(session_arg, **kwargs):  # noqa: ANN001
        row = MagicMock()
        row.id = parent_id if kwargs.get("parent_task_id") is None else child_id
        row.agent_id = None
        row.payload = kwargs.get("payload", {})
        row.swarm_id = kwargs.get("swarm_id")
        created.append(row)
        return row

    with (
        patch(
            "app.application.services.tracer_bullet_kanban.settings.tracer_bullet_kanban_enabled",
            True,
        ),
        patch(
            "app.application.services.tracer_bullet_kanban.create_task_record",
            side_effect=_fake_create,
        ) as mock_create,
        patch(
            "app.application.services.tracer_bullet_kanban._find_existing_slice_set",
            new_callable=AsyncMock,
            return_value=(None, []),
        ),
    ):
        result = await slice_workflow_to_kanban(
            session,
            workflow_id=workflow_id,
            swarm_id=uuid.uuid4(),
            priority=7,
        )

    assert result.slice_count == 1
    assert result.idempotent_reuse is False
    assert mock_create.await_count == 2
    assert created[0].payload.get("tracer_bullet_parent") is True
    assert created[1].payload.get("tracer_bullet_slice") is True
