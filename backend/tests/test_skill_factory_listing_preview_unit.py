"""Unit tests for Skill Factory Monid listing preview on approve."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.application.services.skill_factory_listing_preview import maybe_enrich_listing_preview_on_approve


def _opportunity() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        niche="cursor skills",
        source_refs=[],
    )


def _policy(*, preview: bool = True, video: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        monid_listing_preview_on_approve=preview,
        monid_listing_video_preview_on_approve=video,
    )


@pytest.mark.asyncio
async def test_listing_preview_skipped_when_policy_disabled() -> None:
    out = await maybe_enrich_listing_preview_on_approve(
        AsyncMock(),
        tenant_id=uuid4(),
        opportunity=_opportunity(),
        title="Test Skill",
        policy=_policy(preview=False),
    )
    assert out["skipped"] is True
    assert out["reason"] == "policy_disabled"


@pytest.mark.asyncio
async def test_listing_preview_enriches_hook_without_monid_excerpt(monkeypatch) -> None:
    opp = _opportunity()
    monkeypatch.setattr(
        "app.application.services.skill_factory_listing_preview.monid_connector_ready",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.application.services.skill_factory_listing_preview.gather_monid_listing_signals",
        AsyncMock(return_value=[]),
    )
    session = AsyncMock()
    out = await maybe_enrich_listing_preview_on_approve(
        session,
        tenant_id=uuid4(),
        opportunity=opp,
        title="Newsletter Growth",
        policy=_policy(),
    )
    assert out["ok"] is True
    assert "Newsletter Growth" in out["hook"]
    assert opp.source_refs[0]["kind"] == "listing_preview"
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_listing_preview_video_when_enabled(monkeypatch) -> None:
    opp = _opportunity()
    monkeypatch.setattr(
        "app.application.services.skill_factory_listing_preview.settings",
        SimpleNamespace(skill_factory_monid_video_preview_enabled=True),
    )
    monkeypatch.setattr(
        "app.application.services.skill_factory_listing_preview.monid_connector_ready",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.application.services.skill_factory_listing_preview.gather_monid_listing_signals",
        AsyncMock(
            return_value=[
                {
                    "kind": "external_monid_discover",
                    "excerpt": "Monid hook",
                    "provider": "video_gen",
                    "endpoint": "render",
                },
            ],
        ),
    )
    with patch(
        "app.application.services.skill_factory_listing_preview._maybe_run_monid_video_preview",
        new_callable=AsyncMock,
        return_value="https://cdn.example.com/preview.mp4",
    ) as mock_video:
        out = await maybe_enrich_listing_preview_on_approve(
            AsyncMock(),
            tenant_id=uuid4(),
            opportunity=opp,
            title="Test Skill",
            policy=_policy(video=True),
            dashboard_user_id=uuid4(),
        )
    mock_video.assert_awaited_once()
    assert out["video_preview_url"] == "https://cdn.example.com/preview.mp4"
    assert opp.source_refs[0]["video_preview_url"] == "https://cdn.example.com/preview.mp4"
