"""HTTP contracts for UGC lead magnet content engine."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LeadMagnetCatalogItem(BaseModel):
    """One opinionated swarm lead magnet."""

    model_config = ConfigDict(extra="forbid")

    template_id: str
    name: str
    tagline: str
    description: str
    estimated_minutes: int = Field(ge=1)
    time_saved_hours_per_week: int = Field(ge=0)
    accent_hex: str
    agent_count: int = Field(ge=1)
    headline: str
    landing_url: str
    wizard_url: str


class LeadMagnetLandingResponse(BaseModel):
    """Public landing payload."""

    model_config = ConfigDict(extra="forbid")

    template_id: str
    name: str
    headline: str
    tagline: str
    description: str
    bullets: list[str] = Field(default_factory=list)
    estimated_minutes: int
    time_saved_hours_per_week: int
    accent_hex: str
    agent_count: int
    cta_label: str
    cta_url: str
    landing_url: str


class LeadMagnetShareChannel(BaseModel):
    """One social share format."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    text: str
    char_count: int = Field(ge=0)


class LeadMagnetSharePackResponse(BaseModel):
    """Operator share pack with social copy + optional verified hours."""

    model_config = ConfigDict(extra="forbid")

    template_id: str
    name: str
    headline: str
    tagline: str
    description: str
    bullets: list[str] = Field(default_factory=list)
    estimated_minutes: int
    time_saved_hours_per_week: int
    accent_hex: str
    agent_count: int
    cta_label: str
    cta_url: str
    landing_url: str
    verified_hours_saved: float | None = None
    hours_attribution_line: str
    share_channels: list[LeadMagnetShareChannel] = Field(default_factory=list)
    share_card_markdown: str


__all__ = [
    "LeadMagnetCatalogItem",
    "LeadMagnetLandingResponse",
    "LeadMagnetShareChannel",
    "LeadMagnetSharePackResponse",
]
