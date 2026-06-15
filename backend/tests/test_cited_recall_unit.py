"""Unit tests for MEM2 cited recall panel."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.cited_recall_service import (
    CitedRecallSourceOut,
    compose_cited_recall,
    derive_cited_recall,
)
from app.domain.memory.curated import CuratedFileKind


def test_derive_cited_recall_not_in_memory_when_empty() -> None:
    out = derive_cited_recall(
        query="quantum trading alpha",
        curated_hits=[],
        hive_hits=[],
        session_hits=[],
        vault_hits=[],
    )
    assert out.status == "not_in_memory"
    assert out.in_memory is False
    assert "Not in memory" in out.answer


def test_derive_cited_recall_found_with_strong_hive_hit() -> None:
    hive = [
        CitedRecallSourceOut(
            source_id="hive:del-1",
            source_type="hive_mind",
            label="HiveMind · hero-pack",
            snippet="Verified Gumroad hero pack launch checklist.",
            similarity=0.88,
            href="/knowledge?tab=outputs",
        ),
    ]
    out = derive_cited_recall(
        query="gumroad hero pack",
        curated_hits=[],
        hive_hits=hive,
        session_hits=[],
        vault_hits=[],
    )
    assert out.status == "found"
    assert out.in_memory is True
    assert out.citation_count == 1
    assert "hero pack" in out.answer.lower() or "Gumroad" in out.answer


def test_derive_cited_recall_partial_with_weak_hits() -> None:
    curated = [
        CitedRecallSourceOut(
            source_id="curated:mission",
            source_type="curated_memory",
            label="Brain Pack · Mission",
            snippet="Ship verified harness products.",
            similarity=0.4,
            href="/knowledge?tab=memory#brain-pack",
        ),
    ]
    out = derive_cited_recall(
        query="harness products",
        curated_hits=curated,
        hive_hits=[],
        session_hits=[],
        vault_hits=[],
    )
    assert out.status == "partial"
    assert "Partial recall" in out.answer


def test_derive_cited_recall_short_query_hint() -> None:
    out = derive_cited_recall(
        query="ab",
        curated_hits=[],
        hive_hits=[],
        session_hits=[],
        vault_hits=[],
    )
    assert out.status == "not_in_memory"
    assert "at least 3 characters" in out.answer


@pytest.mark.asyncio
async def test_compose_cited_recall_disabled() -> None:
    session = AsyncMock()
    with patch("app.application.services.cited_recall_service.settings") as mock_settings:
        mock_settings.cited_recall_panel_enabled = False
        out = await compose_cited_recall(session, tenant_id=uuid.uuid4(), query="gumroad launch")
    assert out.enabled is False


@pytest.mark.asyncio
async def test_compose_cited_recall_merges_sources() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    bundle = {
        CuratedFileKind.MISSION: "Launch Gumroad hero pack this week.",
        CuratedFileKind.IDEAL_STATE: "",
        CuratedFileKind.SOUL: "",
        CuratedFileKind.SKILLS_HIERARCHY: "",
        CuratedFileKind.INSTRUCTIONS: "",
        CuratedFileKind.BRAND: "",
    }

    with (
        patch("app.application.services.cited_recall_service.settings") as mock_settings,
        patch(
            "app.application.services.cited_recall_service.CuratedMemoryService",
        ) as mock_service_cls,
        patch(
            "app.application.services.cited_recall_service.semantic_search",
            new_callable=AsyncMock,
            return_value=[
                {
                    "id": "v1",
                    "document": "Hero pack Gumroad listing draft with CTA.",
                    "metadata": {"title": "hero-pack"},
                    "distance": 0.1,
                },
            ],
        ),
        patch(
            "app.application.services.cited_recall_service.search_supervisor_sessions",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.application.services.cited_recall_service.vault_document_recall_for_prompt",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        mock_settings.cited_recall_panel_enabled = True
        mock_settings.hive_mind_enabled = True
        mock_settings.hive_mind_chroma_enabled = True
        mock_settings.hive_mind_max_query_hits_vector = 8
        service = mock_service_cls.return_value
        service.get_bundle = AsyncMock(return_value=bundle)
        out = await compose_cited_recall(session, tenant_id=tenant_id, query="gumroad hero")

    assert out.enabled is True
    assert out.citation_count >= 2
    assert out.in_memory is True
