"""Unit tests for LSP + MCP symbol bridge."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.application.services.lsp.code_symbol_index import (
    extract_goal_identifiers,
    find_references,
    resolve_symbol,
    symbols_in_file,
)
from app.application.services.lsp.lsp_mcp_bridge import (
    build_symbol_context_block,
    invoke_lsp_tool,
    lsp_bridge_registry_rows,
)


def test_symbols_in_file_parses_python_function(tmp_path: Path) -> None:
    """AST indexer should find Python function definitions."""

    rel = "backend/app/sample_hive.py"
    target = tmp_path / rel
    target.parent.mkdir(parents=True)
    target.write_text(
        "def hive_greet(name: str) -> str:\n    return name\n",
        encoding="utf-8",
    )
    symbols = symbols_in_file(tmp_path, rel_path=rel)
    names = {s.name for s in symbols}
    assert "hive_greet" in names


def test_resolve_symbol_finds_exact_match(tmp_path: Path) -> None:
    """Exact symbol name should rank ahead of partial matches."""

    rel = "backend/app/widgets.py"
    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    path.write_text("class WidgetStore:\n    pass\n", encoding="utf-8")
    matches = resolve_symbol(tmp_path, query="WidgetStore")
    assert matches
    assert matches[0].name == "WidgetStore"


def test_find_references_counts_usage(tmp_path: Path) -> None:
    """Reference finder should locate word-boundary mentions."""

    rel = "backend/app/use_widget.py"
    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    path.write_text(
        "from widgets import WidgetStore\n\nstore = WidgetStore()\n",
        encoding="utf-8",
    )
    refs = find_references(tmp_path, symbol_name="WidgetStore", limit=10)
    assert len(refs) >= 2


def test_extract_goal_identifiers_from_backticks() -> None:
    """Goal text with backticks should yield symbol tokens."""

    ids = extract_goal_identifiers("Refactor `HarnessSnapshot` in runtime")
    assert "HarnessSnapshot" in ids


def test_lsp_bridge_registry_empty_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Registry rows should be omitted when feature flag is off."""

    monkeypatch.setattr(
        "app.application.services.lsp.lsp_mcp_bridge.settings.lsp_mcp_bridge_enabled",
        False,
    )
    assert lsp_bridge_registry_rows(goal="test", limit=3) == []


def test_invoke_lsp_tool_resolve_symbol(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tool dispatch should return structured matches."""

    rel = "backend/app/demo.py"
    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    path.write_text("def demo_fn():\n    return 1\n", encoding="utf-8")
    monkeypatch.setattr(
        "app.application.services.lsp.lsp_mcp_bridge.settings.lsp_mcp_bridge_enabled",
        True,
    )
    out = invoke_lsp_tool("resolve_symbol", {"query": "demo_fn"}, repo_root=tmp_path)
    assert out["tool"] == "resolve_symbol"
    assert out["matches"]


def test_build_symbol_context_block_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Context block should be empty when bridge disabled."""

    monkeypatch.setattr(
        "app.application.services.lsp.lsp_mcp_bridge.settings.lsp_mcp_bridge_enabled",
        False,
    )
    assert build_symbol_context_block(goal="Fix HarnessSnapshot") == ""
