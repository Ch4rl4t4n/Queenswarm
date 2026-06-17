"""Unit tests for faceless content pipeline (POS-C)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.faceless_content_pipeline_service import (
    build_faceless_draft_pack,
    compose_faceless_pipeline_snapshot,
    run_faceless_draft,
)
from app.application.services.faceless_content_pipeline_service import FacelessDraftIn
from app.core.config import settings


def test_build_faceless_draft_pack_defaults_schedule() -> None:
    pack = build_faceless_draft_pack(idea="Automate your content with agents", channel="instagram")
    assert pack.simulate_only is True
    assert pack.channel == "instagram"
    assert pack.scheduled_at is not None
    assert "Hook:" in pack.body


@pytest.mark.asyncio
async def test_run_faceless_draft_archives_pack(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "faceless_content_pipeline_enabled", True)

    fake_row = MagicMock()
    fake_row.id = uuid.uuid4()
    fake_row.tags = ["publish_pack", "simulate_only", "publish-pack-verified", "ready_to_publish"]
    fake_row.structured_json = {"channel": "instagram", "body": "Hook: test"}

    with patch(
        "app.application.services.faceless_content_pipeline_service.archive_faceless_publish_pack",
        AsyncMock(return_value=fake_row),
    ):
        with patch(
            "app.application.services.faceless_content_pipeline_service.classify_publish_queue_status",
            return_value="pending",
        ):
            result = await run_faceless_draft(
                AsyncMock(),
                dashboard_user_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                body=FacelessDraftIn(idea="Faceless hook about AI workflows daily"),
            )

    assert result.ok is True
    assert result.deliverable_id == fake_row.id
    assert result.queue_status == "pending"


@pytest.mark.asyncio
async def test_compose_faceless_pipeline_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "faceless_content_pipeline_enabled", False)
    snap = await compose_faceless_pipeline_snapshot(AsyncMock(), dashboard_user_id=uuid.uuid4())
    assert snap.enabled is False
