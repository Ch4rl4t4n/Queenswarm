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
        mock_settings.broker_order_queue_enabled = False
        mock_settings.journal_studio_enabled = False
        mock_settings.journal_studio_gardener_enabled = False
        mock_settings.weekly_compound_gardener_enabled = False
        mock_settings.email_draft_outer_loop_enabled = False
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
                    with patch(
                        "app.application.services.forager_goldmine_dispatch_service.compose_goldmine_alert_inbox_items",
                        new_callable=AsyncMock,
                        return_value=[],
                    ):
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


@pytest.mark.asyncio
async def test_compose_approval_inbox_includes_goldmine_alerts() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    created = datetime.now(tz=UTC)

    with patch("app.application.services.approval_inbox.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        mock_settings.publish_queue_enabled = False
        mock_settings.hive_innovation_lab_enabled = False
        mock_settings.broker_order_queue_enabled = False
        mock_settings.journal_studio_enabled = False
        mock_settings.journal_studio_gardener_enabled = False
        mock_settings.weekly_compound_gardener_enabled = False
        mock_settings.email_draft_outer_loop_enabled = False
        mock_settings.journal_studio_enabled = False
        mock_settings.journal_studio_gardener_enabled = False
        mock_settings.weekly_compound_gardener_enabled = False
        mock_settings.email_draft_outer_loop_enabled = False
        with patch(
            "app.application.services.approval_inbox.list_agent_suggestions",
            new_callable=AsyncMock,
            return_value=[],
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
                with patch(
                    "app.application.services.forager_goldmine_dispatch_service.compose_goldmine_alert_inbox_items",
                    new_callable=AsyncMock,
                    return_value=[
                        {
                            "forager_id": "f1",
                            "forager_name": "YouTube Intel",
                            "source_type": "youtube",
                            "new_item_count": 4,
                            "detail": "4 new signals · Spawn rules: high fit",
                            "skill_bundle": ["competitor-scrape-analyze"],
                        },
                    ],
                ):
                    with patch("app.application.services.approval_inbox.build_catalog") as mock_catalog:
                        mock_catalog.return_value = MagicMock(product_count=1, products=[MagicMock(gumroad_url="x")])
                        with patch("app.application.services.approval_inbox.compose_revenue_summary") as mock_rev:
                            mock_rev.return_value = MagicMock(
                                missing_reports=[],
                                next_operator_action="",
                                scorecard_ready_count=1,
                            )
                            snapshot = await compose_approval_inbox_snapshot(
                                session,
                                tenant_id=tenant_id,
                                dashboard_user_id=user_id,
                                tenant=MagicMock(),
                            )

    assert snapshot.counts.goldmine_alerts == 1
    assert snapshot.counts.total >= 1
    goldmine = next(item for item in snapshot.items if item.kind == "goldmine_alert")
    assert goldmine.source_id == "f1"
    assert goldmine.lane == "intel"


@pytest.mark.asyncio
async def test_compose_approval_inbox_includes_broker_orders() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    created = datetime.now(tz=UTC)

    with patch("app.application.services.approval_inbox.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        mock_settings.publish_queue_enabled = False
        mock_settings.hive_innovation_lab_enabled = False
        mock_settings.broker_order_queue_enabled = True
        mock_settings.journal_studio_enabled = False
        mock_settings.journal_studio_gardener_enabled = False
        mock_settings.weekly_compound_gardener_enabled = False
        mock_settings.email_draft_outer_loop_enabled = False
        with patch(
            "app.application.services.approval_inbox.list_agent_suggestions",
            new_callable=AsyncMock,
            return_value=[],
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
                with patch(
                    "app.application.services.broker_order_queue_service.compose_broker_order_inbox_items",
                    new_callable=AsyncMock,
                    return_value=[
                        {
                            "id": "order-1",
                            "title": "Polymarket order",
                            "detail": "Buy YES",
                            "created_at": created,
                            "venue": "polymarket",
                            "notional_usd": 10.0,
                        },
                    ],
                ):
                    with patch(
                        "app.application.services.forager_goldmine_dispatch_service.compose_goldmine_alert_inbox_items",
                        new_callable=AsyncMock,
                        return_value=[],
                    ):
                        with patch("app.application.services.approval_inbox.build_catalog") as mock_catalog:
                            mock_catalog.return_value = MagicMock(product_count=1, products=[MagicMock(gumroad_url="x")])
                            with patch("app.application.services.approval_inbox.compose_revenue_summary") as mock_rev:
                                mock_rev.return_value = MagicMock(
                                    missing_reports=[],
                                    next_operator_action="",
                                    scorecard_ready_count=1,
                                )
                                snapshot = await compose_approval_inbox_snapshot(
                                    session,
                                    tenant_id=tenant_id,
                                    dashboard_user_id=user_id,
                                    tenant=MagicMock(),
                                )

    assert snapshot.counts.broker_orders == 1
    broker = next(item for item in snapshot.items if item.kind == "broker_order")
    assert broker.source_id == "order-1"
    assert broker.lane == "trading"


@pytest.mark.asyncio
async def test_compose_approval_inbox_includes_journal_drafts() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    created = datetime.now(tz=UTC)

    with patch("app.application.services.approval_inbox.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        mock_settings.publish_queue_enabled = False
        mock_settings.hive_innovation_lab_enabled = False
        mock_settings.broker_order_queue_enabled = False
        mock_settings.journal_studio_enabled = True
        mock_settings.journal_studio_gardener_enabled = True
        mock_settings.weekly_compound_gardener_enabled = False
        mock_settings.email_draft_outer_loop_enabled = False
        with patch(
            "app.application.services.approval_inbox.list_agent_suggestions",
            new_callable=AsyncMock,
            return_value=[],
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
                with patch(
                    "app.application.services.journal_studio_gardener_service.compose_journal_draft_inbox_items",
                    new_callable=AsyncMock,
                    return_value=[
                        {
                            "id": "draft-1",
                            "title": "Journal draft · BTC",
                            "detail": "Wait for confirmation",
                            "created_at": created,
                        },
                    ],
                ):
                    with patch(
                        "app.application.services.forager_goldmine_dispatch_service.compose_goldmine_alert_inbox_items",
                        new_callable=AsyncMock,
                        return_value=[],
                    ):
                        with patch("app.application.services.approval_inbox.build_catalog") as mock_catalog:
                            mock_catalog.return_value = MagicMock(product_count=0, products=[])
                            with patch("app.application.services.approval_inbox.compose_revenue_summary") as mock_rev:
                                mock_rev.return_value = MagicMock(missing_reports=False, next_operator_action="")
                                snapshot = await compose_approval_inbox_snapshot(
                                    session,
                                    tenant_id=tenant_id,
                                    dashboard_user_id=user_id,
                                    tenant=MagicMock(),
                                )

    assert snapshot.counts.journal_drafts == 1
    draft = next(item for item in snapshot.items if item.kind == "journal_draft")
    assert draft.source_id == "draft-1"


@pytest.mark.asyncio
async def test_compose_approval_inbox_skips_gumroad_in_personal_os(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    monkeypatch.setattr("app.core.config.settings.personal_os_mode_enabled", True)

    with patch("app.application.services.approval_inbox.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        mock_settings.publish_queue_enabled = False
        mock_settings.hive_innovation_lab_enabled = False
        mock_settings.broker_order_queue_enabled = False
        mock_settings.journal_studio_enabled = False
        mock_settings.journal_studio_gardener_enabled = False
        mock_settings.weekly_compound_gardener_enabled = False
        mock_settings.email_draft_outer_loop_enabled = False
        with patch(
            "app.application.services.approval_inbox.list_agent_suggestions",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with patch(
                "app.application.services.approval_inbox.compose_four_lane_digest_inbox",
                new_callable=AsyncMock,
            ) as mock_digest:
                from app.application.services.solo_operator_digest_inbox import DigestInboxOut

                mock_digest.return_value = DigestInboxOut(
                    generated_at=datetime.now(tz=UTC),
                    pending_count=0,
                    items=[],
                )
                with patch(
                    "app.application.services.forager_goldmine_dispatch_service.compose_goldmine_alert_inbox_items",
                    new_callable=AsyncMock,
                    return_value=[],
                ):
                    with patch("app.application.services.approval_inbox.build_catalog") as mock_catalog:
                        mock_catalog.return_value = MagicMock(
                            product_count=3,
                            products=[MagicMock(gumroad_url=None) for _ in range(3)],
                        )
                        with patch("app.application.services.approval_inbox.compose_revenue_summary") as mock_rev:
                            mock_rev.return_value = MagicMock(
                                missing_reports=[],
                                next_operator_action="Upload first listing manually: pack-a",
                            )
                            snapshot = await compose_approval_inbox_snapshot(
                                session,
                                tenant_id=tenant_id,
                                dashboard_user_id=user_id,
                                tenant=MagicMock(),
                            )

    assert snapshot.counts.gumroad_manual == 0
    assert "gumroad_manual" not in {item.kind for item in snapshot.items}
