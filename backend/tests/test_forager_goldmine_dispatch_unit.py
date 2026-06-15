"""Unit tests for DG7 forager goldmine dispatch."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.forager_goldmine_dispatch_service import (
    compose_forager_goldmine_alerts,
    derive_forager_skill_bundle,
    promote_forager_goldmine_dispatch,
)


def test_derive_forager_skill_bundle_youtube() -> None:
    bundle = derive_forager_skill_bundle("youtube")
    assert "competitor-scrape-analyze" in bundle
    assert "research" in bundle


def test_derive_forager_skill_bundle_unknown_defaults() -> None:
    bundle = derive_forager_skill_bundle("custom")
    assert bundle == [
        "competitor-scrape-analyze",
        "context",
        "execution-studio",
    ]


@pytest.mark.asyncio
async def test_compose_forager_goldmine_alerts_when_disabled() -> None:
    session = AsyncMock()
    with patch(
        "app.application.services.forager_goldmine_dispatch_service.settings.forager_goldmine_dispatch_enabled",
        False,
    ):
        out = await compose_forager_goldmine_alerts(session, tenant_id=uuid.uuid4())
    assert out.enabled is False
    assert out.alerts == []


@pytest.mark.asyncio
async def test_promote_forager_goldmine_when_missing_forager() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    out = await promote_forager_goldmine_dispatch(
        session,
        tenant_id=uuid.uuid4(),
        forager_id=uuid.uuid4(),
    )
    assert out["ok"] is False
    assert out["error"] == "forager_not_found"


@pytest.mark.asyncio
async def test_promote_forager_goldmine_alert_includes_skill_bundle() -> None:
    tenant_id = uuid.uuid4()
    forager_id = uuid.uuid4()
    forager = MagicMock()
    forager.id = forager_id
    forager.name = "YouTube Intel"
    forager.source_type = "youtube"
    forager.supervisor_routine_id = None

    knowledge_row = MagicMock()
    knowledge_row.id = uuid.uuid4()
    knowledge_row.content_text = "New competitor launch video summary"
    knowledge_row.source_url = "https://youtube.com/watch?v=abc"
    knowledge_row.scraped_at = datetime.now(tz=UTC)

    session = AsyncMock()
    session.scalar = AsyncMock(return_value=forager)

    task_row = MagicMock()
    task_row.id = uuid.uuid4()

    with patch(
        "app.application.services.forager_goldmine_dispatch_service._load_forager_knowledge_rows",
        AsyncMock(return_value=[knowledge_row]),
    ), patch(
        "app.application.services.forager_goldmine_dispatch_service._count_new_forager_items",
        AsyncMock(return_value=3),
    ), patch(
        "app.application.services.forager_goldmine_dispatch_service.create_task_record",
        AsyncMock(return_value=task_row),
    ):
        out = await promote_forager_goldmine_dispatch(
            session,
            tenant_id=tenant_id,
            forager_id=forager_id,
            mode="alert",
            include_skill_bundle=True,
        )

    assert out["ok"] is True
    assert out["mode"] == "alert"
    assert out["new_item_count"] == 3
    assert "competitor-scrape-analyze" in out["skill_slugs"]
    assert "research" in out["skill_slugs"]


@pytest.mark.asyncio
async def test_compose_forager_goldmine_alerts_lists_active_delta() -> None:
    tenant_id = uuid.uuid4()
    forager_id = uuid.uuid4()
    forager = MagicMock()
    forager.id = forager_id
    forager.name = "RSS Jobs"
    forager.source_type = "rss"
    forager.is_active = True
    forager.updated_at = datetime.now(tz=UTC)
    forager.supervisor_routine_id = None

    knowledge_row = MagicMock()
    knowledge_row.id = uuid.uuid4()
    knowledge_row.content_text = "Senior engineer role at Acme"
    knowledge_row.source_url = "https://jobs.example/1"
    knowledge_row.scraped_at = datetime.now(tz=UTC) - timedelta(hours=1)

    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [forager]
    session.execute = AsyncMock(return_value=execute_result)

    with patch(
        "app.application.services.forager_goldmine_dispatch_service.settings.forager_goldmine_dispatch_enabled",
        True,
    ), patch(
        "app.application.services.forager_goldmine_dispatch_service._resolve_alert_since",
        AsyncMock(return_value=datetime.now(tz=UTC) - timedelta(hours=24)),
    ), patch(
        "app.application.services.forager_goldmine_dispatch_service._count_new_forager_items",
        AsyncMock(return_value=2),
    ), patch(
        "app.application.services.forager_goldmine_dispatch_service._load_forager_knowledge_rows",
        AsyncMock(return_value=[knowledge_row]),
    ):
        out = await compose_forager_goldmine_alerts(session, tenant_id=tenant_id)

    assert out.enabled is True
    assert len(out.alerts) == 1
    assert out.alerts[0].forager_id == str(forager_id)
    assert out.alerts[0].new_item_count == 2
    assert out.alerts[0].skill_bundle
