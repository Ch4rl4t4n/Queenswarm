"""Unit tests for unified approval inbox (BA4)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.approval_inbox import compose_approval_inbox_snapshot


@pytest.mark.asyncio
async def test_compose_approval_inbox_disabled_when_control_plane_off() -> None:
    session = AsyncMock()
    with patch("app.application.services.approval_inbox.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = False
        snapshot = await compose_approval_inbox_snapshot(
            session,
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            tenant=MagicMock(),
        )
    assert snapshot.enabled is False


@pytest.mark.asyncio
async def test_compose_approval_inbox_merges_publish_and_suggestions() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    created = datetime.now(tz=UTC)

    class _PublishRow:
        id = uuid.uuid4()
        title = "IG pack"
        body_preview = "Hook line"
        channel = "instagram"
        status = "pending"
        created_at = created

    class _QueueSnap:
        items = [_PublishRow()]

    class _Suggestion:
        id = uuid.uuid4()
        title = "Retry guard"
        description = "Add retry guard"
        proposal_type = "verified_skill_forge"
        created_at = created

    with patch("app.application.services.approval_inbox.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        mock_settings.publish_queue_enabled = True
        mock_settings.hive_innovation_lab_enabled = False
        with patch(
            "app.application.services.approval_inbox.build_publish_queue_snapshot",
            new_callable=AsyncMock,
            return_value=_QueueSnap(),
        ):
            with patch(
                "app.application.services.approval_inbox.list_agent_suggestions",
                new_callable=AsyncMock,
                return_value=[_Suggestion()],
            ):
                with patch(
                    "app.application.services.approval_inbox.compose_four_lane_digest_inbox",
                    new_callable=AsyncMock,
                ) as mock_digest:
                    from app.application.services.solo_operator_digest_inbox import DigestInboxOut

                    mock_digest.return_value = DigestInboxOut(
                        generated_at=created,
                        pending_count=0,
                        items=[],
                    )
                    with patch("app.application.services.approval_inbox.build_catalog") as mock_catalog:
                        mock_catalog.return_value = MagicMock(product_count=0, products=[])
                        with patch("app.application.services.approval_inbox.compose_revenue_summary") as mock_rev:
                            mock_rev.return_value = MagicMock(
                                missing_reports=[],
                                next_operator_action="",
                                scorecard_ready_count=None,
                            )
                            snapshot = await compose_approval_inbox_snapshot(
                                session,
                                tenant_id=tenant_id,
                                dashboard_user_id=user_id,
                                tenant=MagicMock(),
                            )

    assert snapshot.enabled is True
    assert snapshot.counts.publish_queue == 1
    assert snapshot.counts.agent_suggestions == 1
    assert snapshot.counts.total >= 2
    kinds = {item.kind for item in snapshot.items}
    assert "publish_queue" in kinds
    assert "agent_suggestion" in kinds
