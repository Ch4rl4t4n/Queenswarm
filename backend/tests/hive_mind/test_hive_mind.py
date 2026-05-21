"""Unit tests for Phase 0.6 Hive Mind helpers (offline / mocked external IO)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.hive_mind import graph as neo_graph
from app.domain.hive_mind import ingest as ingest_pkg
from app.domain.hive_mind import service as hm_service


def test_summarise_deliverable_prefers_struct_keys() -> None:
    sj = {"summary": "Executive win", "brief_excerpt": "ignored"}
    s, insight = ingest_pkg.summarise_deliverable(sj, "# Title ignored\nSome body.")
    assert s == "Executive win"
    assert isinstance(insight, str) and len(insight.strip()) >= 3


def test_extract_auto_tags_merges_and_bounds() -> None:
    md = "# First Topic\n### Second Thing\nMore\n"
    out = ingest_pkg.extract_auto_tags(md, ["alpha", "ALPHA"])
    assert "alpha" in out


@pytest.mark.asyncio
async def test_query_for_prompt_respects_budget() -> None:
    hits = [
        {
            "document": "doc " * 400,
            "metadata": {"deliverable_id": "00000000-0000-0000-0000-000000000099"},
            "distance": 0.1,
        },
    ]

    class _Cfg(MagicMock):
        hive_mind_enabled = True
        hive_mind_chroma_enabled = True
        hive_mind_max_query_hits_vector = 2
        hive_mind_max_graph_neighbor_breadth = 3
        hive_mind_max_prompt_chars = 200
        hive_mind_selective_recall_enabled = True
        hive_mind_default_recall_mode = "full"
        hive_mind_selective_recall_max_hits = 4
        hive_mind_selective_recall_min_similarity = 0.55
        hive_mind_selective_recall_max_chars = 200
        hive_mind_selective_vault_doc_limit = 0

    cfg = _Cfg()
    with (
        patch("app.domain.hive_mind.service.semantic_search", new_callable=AsyncMock, return_value=hits),
        patch("app.domain.hive_mind.service.neighbor_snapshot_for_prompt", new_callable=AsyncMock, return_value=["line"]),
    ):
        blob = await hm_service.HiveMindService.query_for_prompt(
            relevance_to_current_task="build landing page",
            settings=cfg,
            swarm_id="sw",
            task_id="tk",
            agent_id="ag",
            recall_mode="full",
        )
    assert len(blob) <= 200
    assert "HiveMind" in blob


@pytest.mark.asyncio
async def test_ingest_short_circuits_when_disabled() -> None:
    cfg = MagicMock(hive_mind_enabled=False)
    mock_persist_graph = AsyncMock()

    with patch.object(neo_graph, "persist_hive_graph_bundle", mock_persist_graph):
        await hm_service.HiveMindService.ingest_final_deliverable(row=MagicMock(), settings=cfg, extras=None)

    mock_persist_graph.assert_not_called()
