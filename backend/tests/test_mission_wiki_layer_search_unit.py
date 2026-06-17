"""Unit tests for SB4 wiki-layer hits in mission search."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.mission_wiki_layer_search import (
    _rank_merged_wiki_hits,
    search_mission_wiki_hits,
)
from app.infrastructure.persistence.models.wiki_layer import WikiLayerPageORM


@pytest.mark.asyncio
async def test_search_mission_wiki_hits_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "wiki_layer_enabled", False)
    session = AsyncMock()
    hits = await search_mission_wiki_hits(session, tenant_id=uuid.uuid4(), query="seo")
    assert hits == []


@pytest.mark.asyncio
async def test_search_mission_wiki_hits_lexical_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "wiki_layer_enabled", True)
    monkeypatch.setattr(settings, "wiki_layer_mission_search_enabled", True)

    tenant_id = uuid.uuid4()
    page = WikiLayerPageORM(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        slug="maps-of-content",
        title="Maps of content",
        content_md="SEO pipeline and newsletter loops.",
        char_count=40,
        version=1,
        updated_at=datetime.now(tz=UTC),
    )
    session = AsyncMock()
    session.scalars = AsyncMock(
        side_effect=[
            MagicMock(all=MagicMock(return_value=[page])),
            MagicMock(all=MagicMock(return_value=[])),
        ],
    )

    with patch(
        "app.application.services.mission_wiki_layer_search._semantic_wiki_hits",
        new=AsyncMock(return_value=[]),
    ):
        hits = await search_mission_wiki_hits(session, tenant_id=tenant_id, query="newsletter")

    assert len(hits) == 1
    assert hits[0]["slug"] == "maps-of-content"
    assert hits[0]["kind"] == "wiki_page"
    assert "/knowledge?tab=wiki" in hits[0]["href"]


def test_rank_merged_wiki_hits_boosts_overlap() -> None:
    merged = _rank_merged_wiki_hits(
        [{"wiki_hit_id": "maps-of-content", "match_source": "lexical", "relevance_score": 0.72}],
        [{"wiki_hit_id": "maps-of-content", "match_source": "semantic", "relevance_score": 0.9, "snippet": "vector"}],
        cap=5,
    )
    assert len(merged) == 1
    assert merged[0]["match_source"] == "lexical+semantic"
    assert merged[0]["relevance_score"] == 0.9
