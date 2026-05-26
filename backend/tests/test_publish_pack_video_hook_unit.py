"""Unit tests for Monid TikTok video publish pack hook."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.application.services.publish_pack import PublishPackArtifact
from app.application.services.publish_pack_video_hook import maybe_enrich_tiktok_video_media


def _tiktok_pack() -> PublishPackArtifact:
    return PublishPackArtifact(
        channel="tiktok",
        title="Reel",
        body="Caption",
        hashtags=[],
        cta="",
        media_url=None,
        simulate_only=True,
    )


@pytest.mark.asyncio
async def test_monid_video_hook_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.application.services.publish_pack_video_hook.settings",
        SimpleNamespace(publish_pack_monid_video_hook_enabled=False),
    )
    out = await maybe_enrich_tiktok_video_media(
        AsyncMock(),
        pack=_tiktok_pack(),
        dashboard_user_id=uuid4(),
        tenant=None,
    )
    assert out.media_url is None


@pytest.mark.asyncio
async def test_monid_video_hook_uses_tenant_config(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.application.services.publish_pack_video_hook.settings",
        SimpleNamespace(publish_pack_monid_video_hook_enabled=True),
    )
    tenant = SimpleNamespace(
        operator_settings={
            "publish_lane": {
                "monid_video": {
                    "provider": "video_gen",
                    "endpoint": "render",
                    "input_template": {"prompt": "{{title}}"},
                },
            },
        },
    )
    with (
        patch(
            "app.application.services.publish_pack_video_hook._monid_connector_ready",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.application.services.publish_pack_video_hook.execute_studio_tool",
            new_callable=AsyncMock,
            return_value={"ok": True, "result": '{"url":"https://cdn.example.com/reel.mp4"}'},
        ) as mock_exec,
    ):
        out = await maybe_enrich_tiktok_video_media(
            AsyncMock(),
            pack=_tiktok_pack(),
            dashboard_user_id=uuid4(),
            tenant=tenant,
        )
    mock_exec.assert_called_once()
    assert out.media_url == "https://cdn.example.com/reel.mp4"
