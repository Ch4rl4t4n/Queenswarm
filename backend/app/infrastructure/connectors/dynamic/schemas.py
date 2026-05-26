"""Pydantic payloads for persisted dynamic connectors (plaintext only on the wire toward vault sealing)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class DynamicConnectorSecretsInbound(BaseModel):
    """Inbound secret bundle immediately sealed — never echoed by APIs."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    api_key: str | None = Field(default=None, max_length=4096)
    bearer_token: str | None = Field(default=None, max_length=16384)
    oauth2_access_token: str | None = Field(default=None, max_length=16384)
    oauth2_refresh_token: str | None = Field(default=None, max_length=16384)
    oauth2_token_endpoint: str | None = Field(default=None, max_length=2048)
    oauth2_client_id: str | None = Field(default=None, max_length=512)
    oauth2_client_secret: str | None = Field(default=None, max_length=4096)
    api_key_header_name: str = Field(default="X-API-KEY", max_length=64)
    polymarket_api_key: str | None = Field(default=None, max_length=512)
    polymarket_api_secret: str | None = Field(default=None, max_length=4096)
    polymarket_api_passphrase: str | None = Field(default=None, max_length=512)
    polymarket_wallet_address: str | None = Field(default=None, max_length=128)
    kalshi_api_key_id: str | None = Field(default=None, max_length=128)
    kalshi_private_key_pem: str | None = Field(default=None, max_length=16384)

    def to_sealed_payload(self) -> dict[str, Any]:
        """Return JSON-safe dict handed to vault Fernet sealing."""

        return self.model_dump(mode="json")


AuthTypeLiteral = Literal["none", "api_key", "bearer_token", "oauth2", "polymarket_l2", "kalshi_rsa"]


class DynamicConnectorManifest(BaseModel):
    """Thin MCP-compatible manifest persisted as JSON."""

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    tools: list[dict[str, Any]] = Field(default_factory=list)


class DynamicConnectorCreateBody(BaseModel):
    """Dashboard create form."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    slug: str = Field(..., min_length=2, max_length=160)
    display_name: str = Field(..., min_length=2, max_length=256)
    base_url: AnyHttpUrl | None = None
    auth_type: AuthTypeLiteral = "api_key"
    allowed_manager_slugs: list[str] = Field(default_factory=list)
    mcp_manifest: dict[str, Any] | None = None
    secrets: DynamicConnectorSecretsInbound | None = None

    @field_validator("slug")
    @classmethod
    def slug_lower(cls, v: str) -> str:
        """Normalise slug to hive-safe lowercase."""

        cleaned = v.strip().lower()
        if cleaned == "grokipedia":
            msg = "slug grokipedia is reserved"
            raise ValueError(msg)
        if cleaned[0] not in "abcdefghijklmnopqrstuvwxyz0123456789":
            msg = "slug must begin with alphanumeric"
            raise ValueError(msg)
        if any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for ch in cleaned):
            msg = "slug may contain only lowercase alphanumerics hyphen underscore"
            raise ValueError(msg)
        return cleaned


class DynamicConnectorPatchBody(BaseModel):
    """Partial updates — omit fields to preserve existing ciphertext/manifest."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    display_name: str | None = Field(default=None, min_length=2, max_length=256)
    base_url: AnyHttpUrl | None = None
    auth_type: AuthTypeLiteral | None = None
    allowed_manager_slugs: list[str] | None = None
    mcp_manifest: dict[str, Any] | None = None
    is_active: bool | None = None
    secrets: DynamicConnectorSecretsInbound | None = None


class DynamicConnectorPublic(BaseModel):
    """API projection without ciphertext or secret fields."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: str
    slug: str
    display_name: str
    base_url: str | None
    auth_type: str
    mcp_manifest: dict[str, Any] | None
    allowed_manager_slugs: list[str]
    is_active: bool
    is_builtin: bool
    builtin_kind: str | None
    last_tested_at: str | None


class McpInvokeArgs(BaseModel):
    """Structured args for executor ``mcp_invoke`` synthetic tool."""

    model_config = ConfigDict(extra="forbid")

    connector_slug: str = Field(..., min_length=2, max_length=160)
    tool_name: str = Field(..., min_length=1, max_length=128)
    arguments: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "AuthTypeLiteral",
    "DynamicConnectorCreateBody",
    "DynamicConnectorManifest",
    "DynamicConnectorPatchBody",
    "DynamicConnectorPublic",
    "DynamicConnectorSecretsInbound",
    "McpInvokeArgs",
]
