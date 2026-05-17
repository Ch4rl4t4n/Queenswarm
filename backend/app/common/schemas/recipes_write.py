"""Request bodies for mutating Recipe Library rows (ops + recipe keeper flows)."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecipeCreateBody(BaseModel):
    """Create a catalog-backed workflow recipe."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    topic_tags: list[str] = Field(default_factory=list, max_length=64)
    workflow_template: dict[str, Any]
    created_by_agent_id: uuid.UUID | None = None
    mark_verified: bool = Field(
        default=False,
        description="Stamp ``verified_at`` immediately (promoted recipe).",
    )

    @field_validator("topic_tags", mode="after")
    @classmethod
    def validate_topic_tags(cls, value: list[str]) -> list[str]:
        """Cap tag cardinality and string width for JSONB safety."""

        if len(value) > 64:
            msg = "At most 64 topic tags are allowed."
            raise ValueError(msg)
        for tag in value:
            if len(tag) > 64:
                msg = "Each topic tag must be at most 64 characters."
                raise ValueError(msg)
        return value


class RecipePatchBody(BaseModel):
    """Partial update for leaderboard + imitation metadata."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    topic_tags: list[str] | None = None
    workflow_template: dict[str, Any] | None = None
    is_deprecated: bool | None = None
    mark_verified: bool | None = Field(
        default=None,
        description="When true, sets ``verified_at`` to now; false clears verification.",
    )

    @field_validator("topic_tags", mode="after")
    @classmethod
    def validate_topic_tags(cls, value: list[str] | None) -> list[str] | None:
        """Reuse create-time bounds when tags are present."""

        if value is None:
            return None
        if len(value) > 64:
            msg = "At most 64 topic tags are allowed."
            raise ValueError(msg)
        for tag in value:
            if len(tag) > 64:
                msg = "Each topic tag must be at most 64 characters."
                raise ValueError(msg)
        return value


__all__ = ["RecipeCreateBody", "RecipePatchBody"]
