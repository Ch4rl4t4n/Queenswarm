"""Unit tests for Venice publish pack media hook."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.application.services.publish_pack import PublishPackArtifact
from app.application.services.publish_pack_media_hook import maybe_enrich_publish_pack_media


def _sample_pack() -> PublishPackArtifact:
    return PublishPackArtifact(
        channel="instagram",
        title="Launch",
        body="Hello world",
        hashtags=["ai"],
        cta="Learn more",
        media_url=None,
        simulate_only=True,
    )


@pytest.mark.asyncio
async def test_hook_disabled_returns_unchanged(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.application.services.publish_pack_media_hook.settings",
        SimpleNamespace(publish_pack_venice_media_hook_enabled=False),
    )
    pack = _sample_pack()
    out = await maybe_enrich_publish_pack_media(
        AsyncMock(),
        pack=pack,
        dashboard_user_id=uuid4(),
        tenant=None,
    )
    assert out.media_url is None


@pytest.mark.asyncio
async def test_hook_applies_https_url(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.application.services.publish_pack_media_hook.settings",
        SimpleNamespace(publish_pack_venice_media_hook_enabled=True),
    )
    pack = _sample_pack()
    user_id = uuid4()

    with (
        patch(
            "app.application.services.publish_pack_media_hook._venice_connector_ready",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.application.services.publish_pack_media_hook.execute_studio_tool",
            new_callable=AsyncMock,
            return_value={
                "ok": True,
                "result": '{"url": "https://cdn.venice.ai/generated/post.jpg"}',
            },
        ),
    ):
        out = await maybe_enrich_publish_pack_media(
            AsyncMock(),
            pack=pack,
            dashboard_user_id=user_id,
            tenant=None,
        )
    assert out.media_url == "https://cdn.venice.ai/generated/post.jpg"


@pytest.mark.asyncio
async def test_hook_skips_tiktok_channel(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.application.services.publish_pack_media_hook.settings",
        SimpleNamespace(publish_pack_venice_media_hook_enabled=True),
    )
    pack = _sample_pack().model_copy(update={"channel": "tiktok"})
    with patch(
        "app.application.services.publish_pack_media_hook.execute_studio_tool",
        new_callable=AsyncMock,
    ) as mock_exec:
        out = await maybe_enrich_publish_pack_media(
            AsyncMock(),
            pack=pack,
            dashboard_user_id=uuid4(),
            tenant=None,
        )
    mock_exec.assert_not_called()
    assert out.media_url is None
