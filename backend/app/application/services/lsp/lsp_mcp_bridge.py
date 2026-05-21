"""LSP + MCP bridge — expose symbol tools to supervisor registry and harness API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.application.services.lsp.code_symbol_index import (
    CodeSymbol,
    extract_goal_identifiers,
    find_references,
    resolve_symbol,
    symbols_in_file,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.core.repo_root import resolve_repo_root

_logger = get_logger(__name__)

_CONNECTOR_SLUG = "queenswarm_lsp"
_DISPLAY_NAME = "Queenswarm LSP Bridge"


class LspBridgeDisabledError(RuntimeError):
    """Raised when the LSP bridge feature flag is off."""


class LspBridgeToolError(ValueError):
    """Raised when tool arguments are invalid."""


def _require_enabled() -> None:
    if not settings.lsp_mcp_bridge_enabled:
        msg = "lsp_mcp_bridge_enabled=false — symbol bridge is disabled"
        raise LspBridgeDisabledError(msg)


def _symbol_to_dict(sym: CodeSymbol) -> dict[str, Any]:
    return {
        "name": sym.name,
        "kind": sym.kind,
        "path": sym.path,
        "line": sym.line,
        "signature": sym.signature,
    }


def bridge_status() -> dict[str, Any]:
    """Non-secret deployment status for harness dashboard."""

    repo_root = resolve_repo_root()
    return {
        "enabled": settings.lsp_mcp_bridge_enabled,
        "connector_slug": _CONNECTOR_SLUG,
        "max_results": settings.lsp_mcp_bridge_max_results,
        "scan_roots": ["backend/app", "frontend"],
        "repo_root": str(repo_root),
        "tools": ["resolve_symbol", "list_file_symbols", "find_references"],
    }


def lsp_bridge_registry_rows(*, goal: str | None = None, limit: int = 6) -> list[dict[str, Any]]:
    """Return MCP-style registry rows for builtin LSP tools."""

    if not settings.lsp_mcp_bridge_enabled:
        return []
    cap = max(1, min(int(limit), 12))
    goal_note = (goal or "")[:80]
    base_desc = "Symbol-aware repo context (lightweight AST index, no external LSP daemon)."
    tools = [
        ("resolve_symbol", f"Resolve a class/function/type by name. {base_desc}"),
        ("list_file_symbols", "List definitional symbols in one repo-relative file."),
        ("find_references", "Find word-boundary references to a symbol name."),
    ]
    rows: list[dict[str, Any]] = []
    for name, desc in tools[:cap]:
        rows.append(
            {
                "connector_slug": _CONNECTOR_SLUG,
                "connector_display_name": _DISPLAY_NAME,
                "tool_name": name,
                "description": desc if not goal_note else f"{desc} Goal hint: {goal_note}",
                "method": "POST",
                "path": f"/internal/lsp/{name}",
                "required_permission": None,
                "allowed_manager_slugs": ["coder", "maintainer", "engineer", "scout"],
                "rate_limit_per_minute": 60,
                "is_active": True,
                "source": "lsp_mcp_bridge",
                "score": 0.85,
                "cost_tier": "low",
                "latency_tier": "fast",
            },
        )
    return rows


def invoke_lsp_tool(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Dispatch one builtin LSP MCP tool invocation."""

    _require_enabled()
    root = repo_root or resolve_repo_root()
    max_results = settings.lsp_mcp_bridge_max_results
    max_bytes = settings.lsp_mcp_bridge_max_file_bytes
    name = tool_name.strip()
    if name == "resolve_symbol":
        query = str(arguments.get("query") or arguments.get("symbol") or "").strip()
        if len(query) < 2:
            raise LspBridgeToolError("query must be at least 2 characters")
        matches = resolve_symbol(root, query=query, limit=max_results, max_file_bytes=max_bytes)
        return {"tool": name, "query": query, "matches": [_symbol_to_dict(m) for m in matches]}
    if name == "list_file_symbols":
        rel_path = str(arguments.get("path") or arguments.get("file") or "").strip()
        if not rel_path:
            raise LspBridgeToolError("path is required")
        symbols = symbols_in_file(root, rel_path=rel_path, max_file_bytes=max_bytes)
        return {
            "tool": name,
            "path": rel_path,
            "symbols": [_symbol_to_dict(s) for s in symbols[:max_results]],
        }
    if name == "find_references":
        symbol = str(arguments.get("symbol") or arguments.get("name") or "").strip()
        if len(symbol) < 2:
            raise LspBridgeToolError("symbol must be at least 2 characters")
        refs = find_references(
            root,
            symbol_name=symbol,
            limit=max_results,
            max_file_bytes=max_bytes,
        )
        return {"tool": name, "symbol": symbol, "references": refs}
    msg = f"unknown LSP tool {tool_name!r}"
    raise LspBridgeToolError(msg)


def build_symbol_context_block(*, goal: str, limit: int = 6) -> str:
    """Build a compact prompt block with symbol definitions relevant to a goal."""

    if not settings.lsp_mcp_bridge_enabled:
        return ""
    root = resolve_repo_root()
    identifiers = extract_goal_identifiers(goal)
    if not identifiers:
        return ""
    cap = max(1, min(limit, settings.lsp_mcp_bridge_max_results))
    lines: list[str] = ["=== LSP SYMBOL CONTEXT (MCP bridge) ==="]
    seen: set[tuple[str, str]] = set()
    for ident in identifiers:
        for sym in resolve_symbol(
            root,
            query=ident,
            limit=2,
            max_file_bytes=settings.lsp_mcp_bridge_max_file_bytes,
        ):
            key = (sym.path, sym.name)
            if key in seen:
                continue
            seen.add(key)
            sig = f" — {sym.signature}" if sym.signature else ""
            lines.append(f"- {sym.kind} `{sym.name}` @ {sym.path}:{sym.line}{sig}")
            if len(seen) >= cap:
                break
        if len(seen) >= cap:
            break
    if len(lines) <= 1:
        return ""
    lines.append("=== END LSP SYMBOL CONTEXT ===")
    _logger.info(
        "lsp_mcp_bridge.context_built",
        agent_id="lsp_mcp_bridge",
        swarm_id="",
        task_id="symbol_context",
        symbol_count=len(seen),
    )
    return "\n".join(lines)


def enrich_skill_prompt_with_lsp(skill_prompt: str, *, goal: str, limit: int = 6) -> str:
    """Append symbol context block to a skill prompt when bridge is enabled."""

    block = build_symbol_context_block(goal=goal, limit=limit)
    if not block:
        return skill_prompt
    return f"{skill_prompt}\n\n{block}".strip()


__all__ = [
    "LspBridgeDisabledError",
    "LspBridgeToolError",
    "bridge_status",
    "build_symbol_context_block",
    "enrich_skill_prompt_with_lsp",
    "invoke_lsp_tool",
    "lsp_bridge_registry_rows",
]
