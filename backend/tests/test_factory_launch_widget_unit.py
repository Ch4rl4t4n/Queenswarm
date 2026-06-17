"""Unit tests for REV4 Factory Launch Mission Home widget."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.application.services.factory_launch_widget_service import compose_factory_launch_widget_snapshot
from app.application.services.skill_factory_service import (
    LaunchReadinessOut,
    SkillFactorySnapshotOut,
    SkillFactoryPolicyOut,
    TenantSkillOut,
)


def _skill(
    *,
    slug: str,
    title: str,
    gumroad_product_id: str | None = None,
    gumroad_published: bool | None = None,
) -> TenantSkillOut:
    return TenantSkillOut(
        id=str(uuid.uuid4()),
        slug=slug,
        title=title,
        description="Harness pack",
        version="1.0.0",
        priority=1,
        roles=["operator"],
        keywords=["harness"],
        source="factory",
        recipe_id=None,
        verified_at=datetime.now(tz=UTC),
        github_exported_at=None,
        gumroad_product_id=gumroad_product_id,
        gumroad_published=gumroad_published,
        is_active=True,
    )


def _factory_snapshot(
    *,
    sellable: int = 0,
    launch_queue: list[TenantSkillOut] | None = None,
    gumroad_listing_ready: bool = False,
    gumroad_publish_ready: bool = False,
) -> SkillFactorySnapshotOut:
    return SkillFactorySnapshotOut(
        policy=SkillFactoryPolicyOut(),
        opportunities=[],
        library=[],
        queue_count=0,
        building_count=2,
        launch_readiness=LaunchReadinessOut(
            sellable_count=sellable,
            draft_count=1,
            rejected_count=0,
            gumroad_token_configured=gumroad_listing_ready,
        ),
        launch_queue=launch_queue or [],
        gumroad_listing_ready=gumroad_listing_ready,
        gumroad_publish_ready=gumroad_publish_ready,
    )


@pytest.mark.asyncio
async def test_factory_launch_widget_disabled_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", False)
    session = AsyncMock()

    snapshot = await compose_factory_launch_widget_snapshot(session, tenant_id=uuid.uuid4())

    assert snapshot.enabled is False
    assert "disabled" in snapshot.operator_hint.lower()


@pytest.mark.asyncio
async def test_factory_launch_widget_no_sellable_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(
        "app.application.services.skill_factory_service.compose_skill_factory_snapshot",
        AsyncMock(return_value=_factory_snapshot(sellable=0)),
    )
    session = AsyncMock()

    snapshot = await compose_factory_launch_widget_snapshot(session, tenant_id=uuid.uuid4())

    assert snapshot.enabled is True
    assert snapshot.sellable_count == 0
    assert snapshot.funnel_ready is False
    assert "sellable" in snapshot.operator_hint.lower()


@pytest.mark.asyncio
async def test_factory_launch_widget_funnel_ready_with_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    queue = [_skill(slug="harness-pack", title="Queenswarm Harness Pack")]
    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(
        "app.application.services.skill_factory_service.compose_skill_factory_snapshot",
        AsyncMock(return_value=_factory_snapshot(sellable=1, launch_queue=queue, gumroad_listing_ready=True)),
    )
    session = AsyncMock()

    snapshot = await compose_factory_launch_widget_snapshot(session, tenant_id=uuid.uuid4())

    assert snapshot.funnel_ready is True
    assert snapshot.prepare_available is True
    assert snapshot.gumroad_auto_draft_available is True
    assert snapshot.pending_gumroad_draft_count == 1
    assert snapshot.gumroad_ready is True
    assert snapshot.launch_queue_count == 1
    assert snapshot.top_launch_titles == ["Queenswarm Harness Pack"]
    assert "gumroad drafts" in snapshot.operator_hint.lower()


@pytest.mark.asyncio
async def test_prepare_factory_launch_batch_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", False)
    session = AsyncMock()

    from app.application.services.factory_launch_widget_service import prepare_factory_launch_batch_from_widget

    result = await prepare_factory_launch_batch_from_widget(session, tenant_id=uuid.uuid4())

    assert result.get("ok") is False
    assert result.get("error") == "factory_launch_disabled"


@pytest.mark.asyncio
async def test_prepare_factory_launch_batch_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.skill_factory_launch import LaunchPrepareOut, LaunchPrepareExportOut
    from app.application.services.factory_launch_widget_service import prepare_factory_launch_batch_from_widget
    from app.core.config import settings

    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    mock_prepare = AsyncMock(
        return_value=LaunchPrepareOut(
            exported_count=1,
            sellable_recommended=2,
            message="Exported 1 skill(s).",
            exports=[
                LaunchPrepareExportOut(
                    skill_id=str(uuid.uuid4()),
                    slug="harness-pack",
                    title="Harness Pack",
                    score=0.92,
                    tier="sellable",
                ),
            ],
        ),
    )
    monkeypatch.setattr(
        "app.application.services.skill_factory_launch.prepare_launch_batch",
        mock_prepare,
    )
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    result = await prepare_factory_launch_batch_from_widget(session, tenant_id=tenant_id, limit=3)

    assert result.get("ok") is True
    assert result.get("exported_count") == 1
    mock_prepare.assert_awaited_once_with(session, tenant_id=tenant_id, limit=3)


@pytest.mark.asyncio
async def test_draft_factory_launch_gumroad_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.factory_launch_widget_service import draft_factory_launch_gumroad_from_widget
    from app.core.config import settings

    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_gumroad_listing_enabled", True)
    monkeypatch.setattr(
        "app.application.services.skill_factory_gumroad_listing.gumroad_listing_ready",
        AsyncMock(return_value=False),
    )
    session = AsyncMock()

    result = await draft_factory_launch_gumroad_from_widget(session, tenant_id=uuid.uuid4())

    assert result.get("ok") is False
    assert result.get("error") == "gumroad_not_configured"


@pytest.mark.asyncio
async def test_draft_factory_launch_gumroad_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.factory_launch_widget_service import draft_factory_launch_gumroad_from_widget
    from app.core.config import settings

    skill = _skill(slug="harness-pack", title="Harness Pack")
    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_gumroad_listing_enabled", True)
    monkeypatch.setattr(
        "app.application.services.skill_factory_gumroad_listing.gumroad_listing_ready",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.application.services.skill_factory_service.compose_skill_factory_snapshot",
        AsyncMock(return_value=_factory_snapshot(sellable=1, launch_queue=[skill], gumroad_listing_ready=True)),
    )
    mock_draft = AsyncMock(
        return_value={
            "ok": True,
            "product_id": "prod_abc",
            "product_url": "https://example.gumroad.com/l/harness-pack",
        },
    )
    monkeypatch.setattr(
        "app.application.services.skill_factory_gumroad_listing.create_gumroad_draft_from_skill",
        mock_draft,
    )
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    result = await draft_factory_launch_gumroad_from_widget(session, tenant_id=tenant_id, limit=3)

    assert result.get("ok") is True
    assert result.get("drafted_count") == 1
    assert len(result.get("drafts") or []) == 1
    mock_draft.assert_awaited_once()


@pytest.mark.asyncio
async def test_factory_launch_widget_publish_available(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    queue = [
        _skill(
            slug="harness-pack",
            title="Harness Pack",
            gumroad_product_id="prod_abc",
            gumroad_published=False,
        ),
    ]
    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(
        "app.application.services.skill_factory_service.compose_skill_factory_snapshot",
        AsyncMock(
            return_value=_factory_snapshot(
                sellable=1,
                launch_queue=queue,
                gumroad_listing_ready=True,
                gumroad_publish_ready=True,
            ),
        ),
    )
    session = AsyncMock()

    snapshot = await compose_factory_launch_widget_snapshot(session, tenant_id=uuid.uuid4())

    assert snapshot.gumroad_auto_publish_available is True
    assert snapshot.pending_gumroad_publish_count == 1
    assert "publish" in snapshot.operator_hint.lower()


@pytest.mark.asyncio
async def test_publish_factory_launch_gumroad_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.factory_launch_widget_service import publish_factory_launch_gumroad_from_widget
    from app.core.config import settings

    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_gumroad_publish_enabled", True)
    monkeypatch.setattr(
        "app.application.services.skill_factory_gumroad_listing.gumroad_publish_ready",
        AsyncMock(return_value=False),
    )
    session = AsyncMock()

    result = await publish_factory_launch_gumroad_from_widget(session, tenant_id=uuid.uuid4())

    assert result.get("ok") is False
    assert result.get("error") == "gumroad_not_configured"


@pytest.mark.asyncio
async def test_publish_factory_launch_gumroad_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.factory_launch_widget_service import publish_factory_launch_gumroad_from_widget
    from app.core.config import settings

    skill = _skill(
        slug="harness-pack",
        title="Harness Pack",
        gumroad_product_id="prod_abc",
        gumroad_published=False,
    )
    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_gumroad_publish_enabled", True)
    monkeypatch.setattr(
        "app.application.services.skill_factory_gumroad_listing.gumroad_publish_ready",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.application.services.skill_factory_service.compose_skill_factory_snapshot",
        AsyncMock(
            return_value=_factory_snapshot(
                sellable=1,
                launch_queue=[skill],
                gumroad_listing_ready=True,
                gumroad_publish_ready=True,
            ),
        ),
    )
    mock_publish = AsyncMock(
        return_value={
            "ok": True,
            "product_id": "prod_abc",
            "product_url": "https://example.gumroad.com/l/harness-pack",
            "published": True,
        },
    )
    monkeypatch.setattr(
        "app.application.services.skill_factory_gumroad_listing.publish_gumroad_listing_for_skill",
        mock_publish,
    )
    monkeypatch.setattr(
        "app.application.services.factory_launch_widget_service.sync_factory_launch_catalog_from_widget",
        AsyncMock(return_value={"ok": True, "synced_count": 1, "message": "Synced 1 Gumroad URLs into upload tracker."}),
    )
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    result = await publish_factory_launch_gumroad_from_widget(session, tenant_id=tenant_id, limit=3)

    assert result.get("ok") is True
    assert result.get("published_count") == 1
    assert len(result.get("publishes") or []) == 1
    assert result.get("catalog_sync", {}).get("synced_count") == 1
    mock_publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_factory_launch_revenue_loop_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    queue = [
        _skill(
            slug="harness-pack",
            title="Harness Pack",
            gumroad_product_id="prod_abc",
            gumroad_published=True,
        ),
    ]
    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(settings, "commerce_webhooks_enabled", True)
    monkeypatch.setattr(settings, "gumroad_webhook_secret", "secret-test")
    monkeypatch.setattr(settings, "gumroad_post_purchase_onboarding_enabled", True)
    monkeypatch.setattr(settings, "smtp_user", "ops@example.com")
    monkeypatch.setattr(settings, "smtp_pass", "pass")
    monkeypatch.setattr(
        "app.application.services.skill_factory_service.compose_skill_factory_snapshot",
        AsyncMock(
            return_value=_factory_snapshot(
                sellable=1,
                launch_queue=queue,
                gumroad_listing_ready=True,
                gumroad_publish_ready=True,
            ),
        ),
    )
    session = AsyncMock()

    snapshot = await compose_factory_launch_widget_snapshot(session, tenant_id=uuid.uuid4())

    assert snapshot.published_gumroad_count == 1
    assert snapshot.revenue_loop_ready is True
    assert snapshot.revenue_smoke_available is True
    assert snapshot.catalog_sync_available is True
    assert snapshot.purchase_smoke_available is True
    assert snapshot.full_funnel_available is True
    assert snapshot.launch_and_verify_available is True
    assert "revenue loop closed" in snapshot.operator_hint.lower()


@pytest.mark.asyncio
async def test_run_factory_launch_revenue_smoke_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.factory_launch_widget_service import run_factory_launch_revenue_smoke
    from app.core.config import settings

    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(
        "app.application.services.factory_launch_widget_service.compose_factory_launch_widget_snapshot",
        AsyncMock(
            return_value=type(
                "Snap",
                (),
                {
                    "sellable_count": 1,
                    "published_gumroad_count": 0,
                    "purchase_webhook_ready": False,
                    "post_purchase_onboarding_ready": False,
                    "catalog_sync_available": False,
                },
            )(),
        ),
    )
    session = AsyncMock()

    result = await run_factory_launch_revenue_smoke(session, tenant_id=uuid.uuid4())

    assert result.get("ok") is False
    assert len(result.get("checks") or []) >= 4
    assert "gumroad_webhook_url_template" in result


@pytest.mark.asyncio
async def test_sync_factory_launch_catalog_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.factory_launch_widget_service import sync_factory_launch_catalog_from_widget
    from app.core.config import settings

    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(
        "app.application.services.skill_factory_gumroad_listing.gumroad_listing_ready",
        AsyncMock(return_value=False),
    )
    session = AsyncMock()

    result = await sync_factory_launch_catalog_from_widget(session)

    assert result.get("ok") is False
    assert result.get("error") == "gumroad_not_configured"


@pytest.mark.asyncio
async def test_sync_factory_launch_catalog_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.factory_launch_widget_service import sync_factory_launch_catalog_from_widget
    from app.application.services.gumroad_catalog_sync import GumroadCatalogSyncResult
    from app.core.config import settings

    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(
        "app.application.services.skill_factory_gumroad_listing.gumroad_listing_ready",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.application.services.skill_factory_gumroad_listing._gumroad_token_for_session",
        AsyncMock(return_value="tok_test"),
    )
    monkeypatch.setattr(
        "app.application.services.gumroad_catalog_sync.sync_gumroad_catalog_from_settings",
        AsyncMock(
            return_value=GumroadCatalogSyncResult(
                ok=True,
                synced_count=2,
                api_product_count=2,
                message="Synced 2 Gumroad URLs into upload tracker.",
                state_path="exports/gumroad-upload-status.json",
            ),
        ),
    )
    session = AsyncMock()

    result = await sync_factory_launch_catalog_from_widget(session)

    assert result.get("ok") is True
    assert result.get("synced_count") == 2


@pytest.mark.asyncio
async def test_run_factory_launch_purchase_smoke_no_published(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.factory_launch_widget_service import run_factory_launch_purchase_smoke
    from app.core.config import settings

    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(settings, "factory_launch_purchase_smoke_enabled", True)
    monkeypatch.setattr(
        "app.application.services.skill_factory_service.compose_skill_factory_snapshot",
        AsyncMock(return_value=_factory_snapshot(sellable=1, launch_queue=[])),
    )
    session = AsyncMock()

    result = await run_factory_launch_purchase_smoke(
        session,
        tenant_id=uuid.uuid4(),
        buyer_email="ops@example.com",
    )

    assert result.get("ok") is False
    assert result.get("error") == "no_published_listing"


@pytest.mark.asyncio
async def test_run_factory_launch_purchase_smoke_processes_ping(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.factory_launch_widget_service import run_factory_launch_purchase_smoke
    from app.application.services.gumroad_purchase_unlock import GumroadWebhookResult
    from app.core.config import settings

    skill = _skill(
        slug="harness-pack",
        title="Harness Pack",
        gumroad_product_id="prod_abc",
        gumroad_published=True,
    )
    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(settings, "factory_launch_purchase_smoke_enabled", True)
    monkeypatch.setattr(settings, "commerce_webhooks_enabled", True)
    monkeypatch.setattr(
        "app.application.services.skill_factory_service.compose_skill_factory_snapshot",
        AsyncMock(return_value=_factory_snapshot(sellable=1, launch_queue=[skill], gumroad_publish_ready=True)),
    )
    monkeypatch.setattr(
        "app.application.services.gumroad_purchase_unlock.process_gumroad_webhook_event",
        AsyncMock(
            return_value=GumroadWebhookResult(
                ok=True,
                sale_id="smoke_test",
                ingested=True,
                unlocked=True,
                onboarding_sent=True,
                message="Purchase unlock granted for matching dashboard account.",
            ),
        ),
    )
    monkeypatch.setattr(
        "app.application.services.gumroad_catalog_sync.resolve_slug_for_gumroad_product_id",
        lambda product_id: "harness-pack",
    )
    session = AsyncMock()

    result = await run_factory_launch_purchase_smoke(
        session,
        tenant_id=uuid.uuid4(),
        buyer_email="ops@example.com",
    )

    assert result.get("ok") is True
    assert result.get("unlocked") is True
    assert result.get("onboarding_sent") is True
    assert result.get("catalog_slug") == "harness-pack"


@pytest.mark.asyncio
async def test_run_factory_launch_full_funnel_orchestrates_draft_then_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.application.services.factory_launch_widget_service import run_factory_launch_full_funnel
    from app.core.config import settings

    snap_draft = type(
        "Snap",
        (),
        {
            "gumroad_auto_draft_available": True,
            "gumroad_auto_publish_available": False,
            "catalog_sync_available": False,
            "published_gumroad_count": 0,
            "revenue_loop_ready": False,
        },
    )()
    snap_publish = type(
        "Snap",
        (),
        {
            "gumroad_auto_draft_available": False,
            "gumroad_auto_publish_available": True,
            "catalog_sync_available": False,
            "published_gumroad_count": 0,
            "revenue_loop_ready": False,
        },
    )()
    snap_done = type(
        "Snap",
        (),
        {
            "gumroad_auto_draft_available": False,
            "gumroad_auto_publish_available": False,
            "catalog_sync_available": False,
            "published_gumroad_count": 1,
            "revenue_loop_ready": True,
        },
    )()

    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(
        "app.application.services.factory_launch_widget_service.compose_factory_launch_widget_snapshot",
        AsyncMock(side_effect=[snap_draft, snap_publish, snap_done]),
    )
    monkeypatch.setattr(
        "app.application.services.factory_launch_widget_service.draft_factory_launch_gumroad_from_widget",
        AsyncMock(return_value={"ok": True, "message": "Created 1 Gumroad draft."}),
    )
    monkeypatch.setattr(
        "app.application.services.factory_launch_widget_service.publish_factory_launch_gumroad_from_widget",
        AsyncMock(return_value={"ok": True, "message": "Published 1 Gumroad listing."}),
    )
    session = AsyncMock()

    result = await run_factory_launch_full_funnel(session, tenant_id=uuid.uuid4(), limit=3)

    assert result.get("ok") is True
    steps = result.get("steps") or []
    assert len(steps) == 2
    assert steps[0]["step"] == "gumroad_draft"
    assert steps[1]["step"] == "gumroad_publish"
    assert result.get("published_gumroad_count") == 1
    assert result.get("revenue_loop_ready") is True


@pytest.mark.asyncio
async def test_run_factory_launch_full_funnel_catalog_only(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.factory_launch_widget_service import run_factory_launch_full_funnel
    from app.core.config import settings

    snap_sync = type(
        "Snap",
        (),
        {
            "gumroad_auto_draft_available": False,
            "gumroad_auto_publish_available": False,
            "catalog_sync_available": True,
            "published_gumroad_count": 1,
            "revenue_loop_ready": False,
        },
    )()
    snap_done = type(
        "Snap",
        (),
        {
            "gumroad_auto_draft_available": False,
            "gumroad_auto_publish_available": False,
            "catalog_sync_available": False,
            "published_gumroad_count": 1,
            "revenue_loop_ready": True,
        },
    )()

    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(
        "app.application.services.factory_launch_widget_service.compose_factory_launch_widget_snapshot",
        AsyncMock(side_effect=[snap_sync, snap_done]),
    )
    monkeypatch.setattr(
        "app.application.services.factory_launch_widget_service.sync_factory_launch_catalog_from_widget",
        AsyncMock(return_value={"ok": True, "message": "Synced 1 Gumroad URLs into upload tracker."}),
    )
    session = AsyncMock()

    result = await run_factory_launch_full_funnel(session, tenant_id=uuid.uuid4())

    assert result.get("ok") is True
    steps = result.get("steps") or []
    assert len(steps) == 1
    assert steps[0]["step"] == "catalog_sync"


@pytest.mark.asyncio
async def test_run_factory_launch_launch_and_verify_orchestrates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.application.services.factory_launch_widget_service import run_factory_launch_launch_and_verify
    from app.core.config import settings

    snap_funnel = type(
        "Snap",
        (),
        {
            "full_funnel_available": True,
            "purchase_smoke_available": False,
            "published_gumroad_count": 0,
            "revenue_loop_ready": False,
        },
    )()
    snap_revenue = type(
        "Snap",
        (),
        {
            "full_funnel_available": False,
            "purchase_smoke_available": False,
            "published_gumroad_count": 1,
            "revenue_loop_ready": True,
        },
    )()

    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(
        "app.application.services.factory_launch_widget_service.compose_factory_launch_widget_snapshot",
        AsyncMock(side_effect=[snap_funnel, snap_revenue, snap_revenue]),
    )
    monkeypatch.setattr(
        "app.application.services.factory_launch_widget_service.run_factory_launch_full_funnel",
        AsyncMock(return_value={"ok": True, "message": "Full funnel complete."}),
    )
    monkeypatch.setattr(
        "app.application.services.factory_launch_widget_service.run_factory_launch_revenue_smoke",
        AsyncMock(return_value={"ok": True, "message": "Revenue loop verified."}),
    )
    session = AsyncMock()

    result = await run_factory_launch_launch_and_verify(session, tenant_id=uuid.uuid4(), limit=3)

    assert result.get("ok") is True
    phases = result.get("phases") or []
    assert len(phases) == 2
    assert phases[0]["phase"] == "full_funnel"
    assert phases[1]["phase"] == "revenue_smoke"
    assert result.get("revenue_loop_ready") is True
