"""Unit tests for skill publish asset generators."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.application.services.skill_publish_assets import build_listing_md, build_publish_guide, build_readme_md
from app.infrastructure.persistence.models.recipe import Recipe


def _recipe() -> Recipe:
    return Recipe(
        id=uuid.uuid4(),
        name="Premium — Test Skill",
        description="Test description for listing.",
        topic_tags=["premium-9", "test"],
        workflow_template={"steps": [{"description": "step"}]},
        success_count=5,
        fail_count=1,
        avg_pollen_earned=10.0,
        verified_at=datetime.now(tz=UTC),
    )


def test_build_readme_md_includes_install_command() -> None:
    recipe = _recipe()
    md = build_readme_md(recipe=recipe, slug="test-skill", install_command="npx skills@latest add queenswarm/test-skill")
    assert "# Premium" in md
    assert "npx skills@latest add" in md
    assert "README.md" not in md or "LISTING.md" in md


def test_build_listing_md_includes_price() -> None:
    recipe = _recipe()
    md = build_listing_md(recipe=recipe, slug="test-skill", price_cents=900)
    assert "€9.00" in md
    assert "Gumroad" in md or "Listing" in md


def test_build_publish_guide_has_four_channels() -> None:
    recipe = _recipe()
    guide = build_publish_guide(
        recipe=recipe,
        slug="test-skill",
        install_command="npx skills@latest add queenswarm/test-skill",
    )
    assert len(guide.channels) == 4
    ids = {c.id for c in guide.channels}
    assert ids == {"github", "gumroad", "cursor", "queenswarm"}
    assert guide.suggested_price_eur_cents == 900
    assert len(guide.checklist) >= 4
