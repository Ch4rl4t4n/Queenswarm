"""Unit tests for optional LLM pattern router refinement."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.supervisor.pattern_router import (
    PATTERN_GUARDRAILS,
    PATTERN_PLANNING,
    PATTERN_REFLECTION,
    PATTERN_RAG,
    select_patterns_for_task,
)
from app.application.services.supervisor.pattern_router_llm import (
    _merge_llm_refinement,
    _parse_llm_refinement,
    refine_pattern_selection_with_llm,
)


def test_parse_llm_refinement_when_markdown_wrapped_then_extracts_json() -> None:
    raw = 'Here is JSON:\n{"add_primary": ["rag"], "add_secondary": [], "rationale": "needs retrieval"}'
    payload = _parse_llm_refinement(raw)
    assert payload["add_primary"] == ["rag"]
    assert payload["rationale"] == "needs retrieval"


def test_merge_llm_refinement_preserves_guardrails() -> None:
    heuristic = select_patterns_for_task(goal="test", roles=["coder"])
    merged = _merge_llm_refinement(
        heuristic,
        add_primary=[PATTERN_RAG],
        add_secondary=[],
        llm_rationale="add retrieval",
    )
    assert PATTERN_GUARDRAILS in merged.primary
    assert PATTERN_PLANNING in merged.primary
    assert PATTERN_REFLECTION in merged.primary
    assert PATTERN_RAG in merged.primary
    assert merged.router_version == "heuristic-v1+llm-v1"


@pytest.mark.asyncio
async def test_refine_when_flag_disabled_then_returns_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.supervisor.pattern_router_llm.settings.supervisor_pattern_router_llm_enabled",
        False,
    )
    heuristic = select_patterns_for_task(goal="research competitors", roles=["researcher"])
    db = MagicMock()
    result = await refine_pattern_selection_with_llm(
        db,
        heuristic=heuristic,
        goal="research competitors",
        roles=["researcher"],
    )
    assert result is heuristic
    assert result.router_version == "heuristic-v1"


@pytest.mark.asyncio
async def test_refine_when_llm_suggests_rag_then_merges(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.supervisor.pattern_router_llm.settings.supervisor_pattern_router_llm_enabled",
        True,
    )

    class _FakeRouter:
        async def complete_with_fallback_messages(self, *_args, **_kwargs):  # noqa: ANN001
            return (
                '{"add_primary": ["rag"], "add_secondary": [], "rationale": "research needs docs"}',
                0.001,
            )

    heuristic = select_patterns_for_task(goal="research competitors", roles=["researcher"])
    db = MagicMock()
    result = await refine_pattern_selection_with_llm(
        db,
        heuristic=heuristic,
        goal="research competitors",
        roles=["researcher"],
        litellm_router=_FakeRouter(),  # type: ignore[arg-type]
    )
    assert PATTERN_RAG in result.all_patterns()
    assert result.router_version == "heuristic-v1+llm-v1"
    assert any("llm refine" in r for r in result.rationale)


@pytest.mark.asyncio
async def test_refine_when_llm_fails_then_returns_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.supervisor.pattern_router_llm.settings.supervisor_pattern_router_llm_enabled",
        True,
    )

    router = MagicMock()
    router.complete_with_fallback_messages = AsyncMock(side_effect=RuntimeError("llm down"))

    heuristic = select_patterns_for_task(goal="build api", roles=["coder"])
    db = MagicMock()
    result = await refine_pattern_selection_with_llm(
        db,
        heuristic=heuristic,
        goal="build api",
        roles=["coder"],
        litellm_router=router,
    )
    assert result is heuristic
