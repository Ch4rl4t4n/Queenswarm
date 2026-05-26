"""Unit tests for Morning → Publish pipeline Phase D resolution and steps."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.application.services.morning_publish_pipeline import (
    CONTENT_PUBLISH_LANE_KEY,
    build_pipeline_steps,
    resolve_content_publish_routine,
)
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine


def _routine(
    *,
    name: str,
    context_payload: dict | None = None,
    is_active: bool = True,
) -> SupervisorRoutine:
    return SupervisorRoutine(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        name=name,
        goal_template="Draft publish content",
        is_active=is_active,
        context_payload=context_payload or {},
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


def test_resolve_content_publish_routine_context_payload() -> None:
    tagged = _routine(name="Custom lane", context_payload={CONTENT_PUBLISH_LANE_KEY: True})
    other = _routine(name="Marketing Ops daily")
    routine, binding = resolve_content_publish_routine(routines=[other, tagged])
    assert routine is tagged
    assert binding == "context_payload"


def test_resolve_content_publish_routine_name_pattern() -> None:
    routine, binding = resolve_content_publish_routine(
        routines=[_routine(name="Weekly Content Flywheel draft")],
    )
    assert routine is not None
    assert binding == "name_pattern"
    assert "content flywheel" in routine.name.lower()


def test_resolve_content_publish_routine_missing() -> None:
    routine, binding = resolve_content_publish_routine(
        routines=[_routine(name="Hive maintenance only")],
    )
    assert routine is None
    assert binding == "missing"


def test_build_pipeline_steps_pending_queue() -> None:
    life_lane = {
        "lane_id": "life_os",
        "description": "Morning priorities",
        "binding": "name_pattern",
        "routine_id": str(uuid.uuid4()),
        "routine_name": "Life OS",
        "last_session_status": "completed",
    }
    content = _routine(name="Marketing Ops publish")
    steps = build_pipeline_steps(
        life_os_lane=life_lane,
        content_routine=content,
        content_binding="name_pattern",
        content_last_status="running",
        publish_queue_enabled=True,
        pending_publish_count=2,
    )
    assert len(steps) == 4
    assert steps[0].status == "done"
    assert steps[1].status == "running"
    assert steps[2].status == "done"
    assert steps[3].status == "pending"
    assert steps[3].id == "publish_queue"


def test_build_pipeline_steps_skips_unbound_lanes() -> None:
    steps = build_pipeline_steps(
        life_os_lane={"binding": "missing", "description": "Unbound"},
        content_routine=None,
        content_binding="missing",
        content_last_status=None,
        publish_queue_enabled=False,
        pending_publish_count=0,
    )
    assert steps[0].status == "skipped"
    assert steps[1].status == "skipped"
    assert steps[3].status == "blocked"
