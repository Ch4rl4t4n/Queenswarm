"""Unit coverage for premium skill checkout helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.application.services.skill_marketplace_policy import is_premium_recipe, resolve_skill_price_cents
from app.infrastructure.persistence.models.recipe import Recipe


def test_is_premium_recipe_when_premium_tag_then_true() -> None:
    recipe = Recipe(
        name="x",
        description=None,
        topic_tags=["premium", "api"],
        workflow_template={"steps": []},
        success_count=0,
        fail_count=0,
        avg_pollen_earned=0.0,
        embedding_id=None,
        created_by_agent_id=None,
        verified_at=datetime.now(tz=UTC),
        last_used_at=None,
        is_deprecated=False,
    )
    assert is_premium_recipe(recipe) is True


def test_is_premium_recipe_when_no_premium_tag_then_false() -> None:
    recipe = Recipe(
        name="x",
        description=None,
        topic_tags=["api"],
        workflow_template={"steps": []},
        success_count=0,
        fail_count=0,
        avg_pollen_earned=0.0,
        embedding_id=None,
        created_by_agent_id=None,
        verified_at=datetime.now(tz=UTC),
        last_used_at=None,
        is_deprecated=False,
    )
    assert is_premium_recipe(recipe) is False


def test_resolve_skill_price_cents_when_premium_9_tag() -> None:
    recipe = Recipe(
        name="x",
        description=None,
        topic_tags=["premium-9"],
        workflow_template={"steps": []},
        success_count=0,
        fail_count=0,
        avg_pollen_earned=0.0,
        embedding_id=None,
        created_by_agent_id=None,
        verified_at=None,
        last_used_at=None,
        is_deprecated=False,
    )
    assert resolve_skill_price_cents(recipe) == 900
