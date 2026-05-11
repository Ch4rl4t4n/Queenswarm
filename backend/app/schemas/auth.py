"""HTTP contracts for swarm JWT exchange."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TokenMintRequest(BaseModel):
    """Inbound subject override for scripted bees and dashboard operators."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    subject: str = Field(
        default="hive-operator",
        min_length=1,
        max_length=256,
        description='JWT ``sub`` (e.g. ``operator:alice``, ``bee:sim-uuid``)',
    )
    expires_minutes: int | None = Field(
        default=None,
        ge=1,
        le=1440,
        description="Optional shorter TTL overriding ``ACCESS_TOKEN_EXPIRE_MINUTES``.",
    )
    scope: str | None = Field(
        default=None,
        max_length=512,
        description="Optional space-separated OAuth scopes stored on the JWT (e.g. ``recipes:write``).",
    )


class TokenIssued(BaseModel):
    """Canonical OAuth2-compatible envelope for Bearer usage."""

    model_config = ConfigDict(extra="ignore")

    access_token: str
    token_type: str = Field(default="bearer")
    expires_in: int = Field(ge=1, description="Access token TTL in seconds.")


__all__ = ["TokenIssued", "TokenMintRequest"]
