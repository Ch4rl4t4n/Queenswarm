from __future__ import annotations

from app.application.services.skill_factory_publish import (
    _is_generic_factory_skill_title,
    _opportunity_product_title,
)
from app.application.services.skill_factory_service import slugify_skill_name


def test_is_generic_factory_skill_title_when_fallback_draft() -> None:
    assert _is_generic_factory_skill_title("Skill Factory draft") is True
    assert _is_generic_factory_skill_title("skill-factory-output") is True
    assert _is_generic_factory_skill_title("Newsletter Growth Loop") is False


def test_opportunity_product_title_strips_skill_pack_prefix() -> None:
    from types import SimpleNamespace

    row = SimpleNamespace(title="Skill pack: SEO blog pipeline for indie hackers")
    assert _opportunity_product_title(row) == "SEO blog pipeline for indie hackers"  # type: ignore[arg-type]


def test_slugify_distinct_niches_produce_distinct_slugs() -> None:
    a = slugify_skill_name("SEO blog pipeline for indie hackers")
    b = slugify_skill_name("Newsletter growth automation")
    assert a != b
