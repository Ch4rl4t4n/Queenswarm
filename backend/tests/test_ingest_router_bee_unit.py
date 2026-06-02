"""Ingest router + YouTube transcript bee unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.ingest_router_bee import resolve_ingest_source
from app.application.services.youtube_transcript_bee import (
    extract_youtube_video_id,
    is_youtube_url,
)


def test_extract_youtube_video_id_watch_url() -> None:
    vid = extract_youtube_video_id("https://www.youtube.com/watch?v=QZMljuD10sU")
    assert vid == "QZMljuD10sU"


def test_extract_youtube_video_id_short_url() -> None:
    vid = extract_youtube_video_id("https://youtu.be/pCqpuHA8kHM")
    assert vid == "pCqpuHA8kHM"


def test_is_youtube_url_rejects_article() -> None:
    assert is_youtube_url("https://queenswarm.love/manual") is False


@pytest.mark.asyncio
async def test_resolve_ingest_source_youtube_route() -> None:
    with patch("app.application.services.ingest_router_bee.settings") as mock_settings:
        mock_settings.youtube_transcript_bee_enabled = True
        mock_settings.research_bee_max_chars = 8000
        with patch(
            "app.application.services.ingest_router_bee.fetch_youtube_transcript",
            new=AsyncMock(
                return_value=type(
                    "YT",
                    (),
                    {
                        "transcript_text": "Alpha beta gamma transcript content here.",
                        "title": "Demo video",
                        "video_id": "abc12345678",
                        "language": "en",
                        "source_url": "https://www.youtube.com/watch?v=abc12345678",
                    },
                )(),
            ),
        ):
            resolved = await resolve_ingest_source(
                source_url="https://www.youtube.com/watch?v=abc12345678",
            )
    assert resolved.ingest_route == "youtube"
    assert resolved.video_id == "abc12345678"
    assert "transcript" in resolved.raw_text


@pytest.mark.asyncio
async def test_resolve_ingest_source_paste_route() -> None:
    with patch("app.application.services.ingest_router_bee.settings") as mock_settings:
        mock_settings.research_bee_max_chars = 8000
        resolved = await resolve_ingest_source(content_text="Paste lane content for brief.")
    assert resolved.ingest_route == "paste"
