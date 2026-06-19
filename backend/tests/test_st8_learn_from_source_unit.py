"""Unit tests for HN6 learn-from-source and CE6 Reddit live policy."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.community_engagement_policy import reddit_live_post_allowed
from app.application.services.learn_from_source_service import (
    LearnFromSourceIn,
    submit_learn_from_source,
)
from app.core import config


def test_reddit_live_post_allowed_when_disabled() -> None:
    with patch.object(config.settings, "reddit_live_enabled", False):
        with patch.object(config.settings, "reddit_live_max_posts_per_day", 3):
            ok, reason = reddit_live_post_allowed(posts_today=0)
    assert ok is False
    assert reason == "reddit_live_disabled"


def test_reddit_live_post_allowed_when_cap_zero() -> None:
    with patch.object(config.settings, "reddit_live_enabled", True):
        with patch.object(config.settings, "reddit_live_max_posts_per_day", 0):
            ok, reason = reddit_live_post_allowed(posts_today=0)
    assert ok is False
    assert reason == "reddit_live_cap_zero"


def test_reddit_live_post_allowed_when_under_cap() -> None:
    with patch.object(config.settings, "reddit_live_enabled", True):
        with patch.object(config.settings, "reddit_live_max_posts_per_day", 2):
            ok, reason = reddit_live_post_allowed(posts_today=1)
    assert ok is True
    assert reason == "ok"


@pytest.mark.asyncio
async def test_submit_learn_from_source_delegates_to_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "learn_from_source_enabled", True)
    monkeypatch.setattr(config.settings, "video_url_batch_wizard_enabled", True)

    batch_out = MagicMock()
    batch_out.task_id = uuid.uuid4()
    batch_out.deliverable_id = uuid.uuid4()
    batch_out.knowledge_ids = ["k1"]
    batch_out.gardener_triggered = True

    async def _fake_batch(*_a, **_k):  # noqa: ANN001
        return batch_out

    monkeypatch.setattr(
        "app.application.services.learn_from_source_service.submit_video_url_batch_wizard",
        _fake_batch,
    )

    db = AsyncMock()
    result = await submit_learn_from_source(
        db,
        tenant_id=uuid.uuid4(),
        dashboard_user_id=uuid.uuid4(),
        body=LearnFromSourceIn(url="https://example.com/article"),
    )
    assert result.learn_from_source is True
    assert result.task_id
    assert "task=" in result.tasks_href
