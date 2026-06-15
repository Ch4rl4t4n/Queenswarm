"""Unit tests for NP8 Video URL batch wizard."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.video_url_batch_service import (
    VideoUrlBatchSubmitIn,
    VideoUrlIntelItemOut,
    compose_batch_digest_markdown,
    compose_video_url_batch_wizard_snapshot,
    fetch_url_batch_intel,
    parse_url_batch,
    submit_video_url_batch_wizard,
)


def test_parse_url_batch_dedupes_and_caps() -> None:
    raw = (
        "https://youtu.be/abc12345678\n"
        "https://youtu.be/abc12345678\n"
        "https://example.com/post\n"
    )
    urls = parse_url_batch(raw, max_urls=5)
    assert urls == ["https://youtu.be/abc12345678", "https://example.com/post"]


def test_compose_batch_digest_markdown_includes_summary() -> None:
    items = [
        VideoUrlIntelItemOut(
            url="https://youtu.be/abc12345678",
            title="Demo video",
            platform="youtube",
            status="ok",
            excerpt="Hello transcript excerpt.",
            transcript_available=True,
            transcript_language="en",
        ),
    ]
    title, md = compose_batch_digest_markdown(items, title="Batch review")
    assert title == "Batch review"
    assert "## Batch summary" in md
    assert "Demo video" in md


def test_compose_snapshot_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "video_url_batch_wizard_enabled", False)
    snap = compose_video_url_batch_wizard_snapshot()
    assert snap.enabled is False


@pytest.mark.asyncio
async def test_fetch_url_batch_intel_isolates_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_fetch(url: str, *, excerpt_chars: int | None = None) -> VideoUrlIntelItemOut:  # noqa: ARG001
        if "fail" in url:
            raise RuntimeError("network down")
        return VideoUrlIntelItemOut(
            url=url,
            title="OK",
            platform="web",
            status="ok",
            excerpt="text",
        )

    monkeypatch.setattr(
        "app.application.services.video_url_batch_service.fetch_url_intel",
        _fake_fetch,
    )
    rows = await fetch_url_batch_intel(["https://example.com/a", "https://fail.example.com/x"])
    assert len(rows) == 2
    assert rows[0].status == "ok"
    assert rows[1].status == "error"


@pytest.mark.asyncio
async def test_submit_video_url_batch_wizard_creates_task(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "video_url_batch_wizard_enabled", True)
    monkeypatch.setattr(config.settings, "wiki_layer_enabled", False)

    sample_items = [
        VideoUrlIntelItemOut(
            url="https://youtu.be/abc12345678",
            title="Demo",
            platform="youtube",
            status="ok",
            excerpt="Excerpt",
            transcript_available=True,
        ),
    ]

    with patch(
        "app.application.services.video_url_batch_service.parse_url_batch",
        return_value=["https://youtu.be/abc12345678"],
    ), patch(
        "app.application.services.video_url_batch_service.fetch_url_batch_intel",
        new=AsyncMock(return_value=sample_items),
    ), patch(
        "app.application.services.video_url_batch_service.create_mission_triage_task",
        new=AsyncMock(return_value=SimpleNamespace(task=SimpleNamespace(id=uuid.uuid4()))),
    ), patch(
        "app.application.services.video_url_batch_service.OutputEngine.create_final_deliverable",
        new=AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4())),
    ):
        result = await submit_video_url_batch_wizard(
            AsyncMock(),
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            body=VideoUrlBatchSubmitIn(
                urls_text="https://youtu.be/abc12345678",
                wiki_capture=False,
            ),
        )

    assert result.ok is True
    assert result.url_count == 1
    assert result.ok_count == 1
