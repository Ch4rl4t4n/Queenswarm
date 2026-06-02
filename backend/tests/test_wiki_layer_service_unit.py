"""Unit tests for Wiki Layer service and retrieval tier helpers."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.wiki_layer_service import (
    WikiLayerService,
    _extract_project_briefs,
    normalize_retrieval_tier,
)
from app.domain.memory.curated import CuratedFileKind


def test_normalize_retrieval_tier_defaults_to_wiki_only() -> None:
    assert normalize_retrieval_tier(None) == "wiki_only"
    assert normalize_retrieval_tier("DEEP_RAW") == "deep_raw"
    assert normalize_retrieval_tier("unknown") == "wiki_only"


def test_extract_project_briefs_from_section() -> None:
    md = "# Mission\nfoo\n\n## Project briefs\nBuild Queenswarm solo operator.\n\n## Other\nbar"
    assert "Queenswarm solo" in _extract_project_briefs(md)


def test_wiki_layer_service_compile_operator_context() -> None:
    svc = WikiLayerService(db=MagicMock())
    bundle = {
        CuratedFileKind.MISSION: "Ship verified workflows.",
        CuratedFileKind.IDEAL_STATE: "",
        CuratedFileKind.SOUL: "Bee-hive pragmatist.",
        CuratedFileKind.SKILLS_HIERARCHY: "",
        CuratedFileKind.INSTRUCTIONS: "",
    }
    out = svc._compile_operator_context(bundle)
    assert "Ship verified" in out
    assert "Bee-hive" in out


@pytest.mark.asyncio
async def test_render_wiki_prompt_block_empty_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "wiki_layer_enabled", False)
    db = AsyncMock()
    svc = WikiLayerService(db=db)
    out = await svc.render_wiki_prompt_block(uuid.uuid4())
    assert out == ""


def test_shared_context_wiki_only_alias() -> None:
    from app.application.services.supervisor.shared_context import SharedContextService

    svc = SharedContextService()
    sections = svc.parse_retrieval_contract("wiki_only")
    assert "policy" in sections
    assert "semantic_memory" not in sections


def test_shared_context_deep_raw_alias() -> None:
    from app.application.services.supervisor.shared_context import SharedContextService

    svc = SharedContextService()
    sections = svc.parse_retrieval_contract("deep_raw")
    assert "semantic_memory" in sections
    assert "hybrid_memory" in sections
