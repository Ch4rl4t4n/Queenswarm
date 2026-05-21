"""HTTP contracts for LSP + MCP bridge harness API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LspResolveRequest(BaseModel):
    """Resolve a symbol name across the monorepo index."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    query: str = Field(..., min_length=2, max_length=200)


class LspFileSymbolsRequest(BaseModel):
    """List symbols defined in one repo-relative file."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    path: str = Field(..., min_length=3, max_length=500)


class LspFindReferencesRequest(BaseModel):
    """Find references to a symbol name."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    symbol: str = Field(..., min_length=2, max_length=200)


class LspToolInvokeRequest(BaseModel):
    """Generic MCP-style tool dispatch for harness testing."""

    model_config = ConfigDict(extra="ignore")

    tool_name: str = Field(..., min_length=3, max_length=64)
    arguments: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "LspFileSymbolsRequest",
    "LspFindReferencesRequest",
    "LspResolveRequest",
    "LspToolInvokeRequest",
]
