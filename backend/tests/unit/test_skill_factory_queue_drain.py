"""Unit tests for Skill Factory queue drain."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.skill_factory_queue_drain import (
    _forge_needs_rebuild,
    _forge_ready_to_approve,
    drain_skill_factory_queue,
)
from app.application.services.skill_factory_service import SkillFactoryPolicyOut


def test_forge_needs_rebuild_when_quality_or_critic_fail() -> None:
    assert _forge_needs_rebuild(quality_passed=False, critic_approved=True) is True
    assert _forge_needs_rebuild(quality_passed=True, critic_approved=False) is True
    assert _forge_needs_rebuild(quality_passed=True, critic_approved=True) is False


def test_forge_payload_fields_infer_failure_from_issues() -> None:
    from app.application.services.skill_factory_service import _forge_payload_fields

    quality, critic, issues = _forge_payload_fields(
        SimpleNamespace(
            proposal_payload={"issues": ["critic_not_approved"], "skill_valid": True},
        ),
    )
    assert quality is False
    assert critic is False
    assert issues == ["critic_not_approved"]


def test_factory_progress_fields_for_awaiting_forge_fail() -> None:
    from types import SimpleNamespace

    from app.application.services.skill_factory_service import _factory_progress_fields

    row = SimpleNamespace(status="awaiting_forge")
    phase, label, detail = _factory_progress_fields(
        row,
        supervisor_session_status="completed",
        supervisor_session_error=None,
        forge_quality_passed=False,
        forge_critic_approved=False,
        forge_issues=["critic_not_approved"],
    )
    assert phase == "forge_failed"
    assert "rebuild" in label.lower()
    assert detail is not None


def test_forge_ready_to_approve_requires_both_gates() -> None:
    assert _forge_ready_to_approve(quality_passed=True, critic_approved=True) is True
    assert _forge_ready_to_approve(quality_passed=False, critic_approved=True) is False


@pytest.mark.asyncio
async def test_drain_rebuilds_failed_forge_by_score_order() -> None:
    tenant_id = uuid.uuid4()
    low = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        status="awaiting_forge",
        composite_score=0.5,
        supervisor_session_id=uuid.uuid4(),
    )
    high = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        status="awaiting_forge",
        composite_score=0.9,
        supervisor_session_id=uuid.uuid4(),
    )
    forge_low = SimpleNamespace(
        status="pending",
        proposal_payload={"quality_gate_passed": False, "critic_approved": False},
    )
    forge_high = SimpleNamespace(
        status="pending",
        proposal_payload={"quality_gate_passed": False, "critic_approved": False},
    )
    session = AsyncMock()
    policy = SkillFactoryPolicyOut(
        auto_queue_drain_enabled=True,
        auto_rebuild_failed_forges=True,
        drain_batch_per_tick=1,
    )

    rebuild_mock = AsyncMock(
        side_effect=[
            SimpleNamespace(status="building"),
        ],
    )

    with (
        patch(
            "app.application.services.skill_factory_queue_drain.list_skill_opportunities",
            AsyncMock(return_value=[low, high]),
        ),
        patch(
            "app.application.services.skill_factory_queue_drain._count_building",
            AsyncMock(return_value=0),
        ),
        patch(
            "app.application.services.skill_factory_queue_drain._forge_suggestions_by_session",
            AsyncMock(
                return_value={
                    low.supervisor_session_id: forge_low,
                    high.supervisor_session_id: forge_high,
                },
            ),
        ),
        patch(
            "app.application.services.skill_factory_queue_drain.rebuild_factory_opportunity",
            rebuild_mock,
        ),
    ):
        result = await drain_skill_factory_queue(session, tenant_id=tenant_id, policy=policy)

    assert result.rebuilt == 1
    rebuild_mock.assert_awaited_once()
    assert rebuild_mock.await_args.kwargs["opportunity_id"] == high.id


@pytest.mark.asyncio
async def test_drain_rebuilds_approved_forge_with_quality_fail() -> None:
    """Approved forges with failed quality/critic must still enter rebuild loop."""

    tenant_id = uuid.uuid4()
    row = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        status="awaiting_forge",
        composite_score=0.88,
        supervisor_session_id=uuid.uuid4(),
    )
    forge = SimpleNamespace(
        status="approved",
        proposal_payload={
            "quality_gate_passed": False,
            "critic_approved": False,
            "issues": ["critic_not_approved"],
        },
    )
    session = AsyncMock()
    policy = SkillFactoryPolicyOut(
        auto_queue_drain_enabled=True,
        auto_rebuild_failed_forges=True,
        drain_batch_per_tick=2,
        max_concurrent_builds=10,
    )
    rebuild_mock = AsyncMock(return_value=SimpleNamespace(status="building"))

    with (
        patch(
            "app.application.services.skill_factory_queue_drain.list_skill_opportunities",
            AsyncMock(return_value=[row]),
        ),
        patch(
            "app.application.services.skill_factory_queue_drain._count_building",
            AsyncMock(return_value=0),
        ),
        patch(
            "app.application.services.skill_factory_queue_drain._forge_suggestions_by_session",
            AsyncMock(return_value={row.supervisor_session_id: forge}),
        ),
        patch(
            "app.application.services.skill_factory_queue_drain.rebuild_factory_opportunity",
            rebuild_mock,
        ),
    ):
        result = await drain_skill_factory_queue(session, tenant_id=tenant_id, policy=policy)

    assert result.rebuilt == 1
    rebuild_mock.assert_awaited_once_with(
        session,
        tenant_id=tenant_id,
        opportunity_id=row.id,
        created_by_subject="celery:skill_factory_drain",
        reviewer_subject="celery:skill_factory_drain",
    )
