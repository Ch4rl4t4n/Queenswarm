"""Read-only snapshot model for MCP Ops Studio workspace cards."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class McpCatalogRowOut(BaseModel):
    """Catalog provider row for MCP discovery section."""

    model_config = ConfigDict(extra="ignore")

    provider: str
    trust_tier: Literal["verified", "community"]
    tool_count: int = 0
    auth_mode: Literal["oauth", "api_key"]


class McpInstallRowOut(BaseModel):
    """Governed install queue row."""

    model_config = ConfigDict(extra="ignore")

    provider: str
    requested_by: str
    stage: Literal["policy_review", "pending_approval"]


class McpHealthRowOut(BaseModel):
    """Read-only health diagnostics row."""

    model_config = ConfigDict(extra="ignore")

    provider: str
    status: Literal["healthy", "degraded"]
    checked_at: str


class McpOpsStudioSnapshotOut(BaseModel):
    """Unified read model for MCP Ops Studio sections."""

    model_config = ConfigDict(extra="ignore")

    generated_at: datetime
    source: Literal["read_only_mock"] = "read_only_mock"
    catalog: list[McpCatalogRowOut] = Field(default_factory=list)
    install: list[McpInstallRowOut] = Field(default_factory=list)
    health: list[McpHealthRowOut] = Field(default_factory=list)


def compose_mcp_ops_studio_snapshot() -> McpOpsStudioSnapshotOut:
    """Compose read-only MCP Ops snapshot for section cards."""

    return McpOpsStudioSnapshotOut(
        generated_at=datetime.now(tz=UTC),
        catalog=[
            McpCatalogRowOut(provider="GitHub MCP", trust_tier="verified", tool_count=8, auth_mode="oauth"),
            McpCatalogRowOut(provider="Notion MCP", trust_tier="community", tool_count=5, auth_mode="api_key"),
        ],
        install=[
            McpInstallRowOut(provider="Linear MCP", requested_by="operator", stage="policy_review"),
        ],
        health=[],
    )


__all__ = ["McpOpsStudioSnapshotOut", "compose_mcp_ops_studio_snapshot"]
