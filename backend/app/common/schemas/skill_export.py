"""HTTP contracts for Recipe → Cursor/Claude skill export bundles."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SkillExportFile(BaseModel):
    """One file inside an export bundle (relative path → UTF-8 content)."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=260)
    content: str


class SkillExportMeta(BaseModel):
    """Verification + hive telemetry surfaced to marketplaces."""

    model_config = ConfigDict(extra="forbid")

    source: str = "queenswarm.love"
    recipe_id: uuid.UUID
    recipe_name: str
    slug: str
    verified: bool
    verified_at: datetime | None = None
    success_rate: float = Field(ge=0.0, le=1.0)
    avg_pollen_earned: float = Field(ge=0.0)
    success_count: int = Field(ge=0)
    fail_count: int = Field(ge=0)
    topic_tags: list[str] = Field(default_factory=list)
    export_version: str = "1.0.0"


class SkillExportResponse(BaseModel):
    """Full Matt Pocock-style bundle for one-click install flows."""

    model_config = ConfigDict(extra="forbid")

    meta: SkillExportMeta
    files: list[SkillExportFile]
    install_command: str
    install_hint: str


class SkillCatalogBuiltinItem(BaseModel):
    """Built-in hive Markdown skill (supervisor SkillLibrary)."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    version: str
    roles: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    kind: str = "builtin"


class SkillCatalogRecipeItem(BaseModel):
    """Verified recipe eligible for skill export."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    verified_at: datetime | None = None
    topic_tags: list[str] = Field(default_factory=list)
    success_rate: float = Field(ge=0.0, le=1.0)
    avg_pollen_earned: float = Field(ge=0.0)
    kind: str = "recipe"
    premium: bool = False
    price_eur_cents: int = Field(default=0, ge=0)
    unlocked: bool = True


class SkillCatalogResponse(BaseModel):
    """Public-ish catalog for integrations UI (JWT gated)."""

    model_config = ConfigDict(extra="forbid")

    builtin: list[SkillCatalogBuiltinItem] = Field(default_factory=list)
    recipes: list[SkillCatalogRecipeItem] = Field(default_factory=list)


class HiveMdResponse(BaseModel):
    """Generated HIVE.md for a sub-swarm colony."""

    model_config = ConfigDict(extra="forbid")

    swarm_id: uuid.UUID
    swarm_name: str
    content: str
    generated_at: datetime
    extras: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "HiveMdResponse",
    "SkillCatalogBuiltinItem",
    "SkillCatalogRecipeItem",
    "SkillCatalogResponse",
    "SkillExportFile",
    "SkillExportMeta",
    "SkillExportResponse",
]
