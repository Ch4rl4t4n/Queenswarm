"""Unit tests for skill sellable classification."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.application.services.skill_factory_sellable import assess_tenant_skill_sellable


def _skill(**kwargs: object) -> SimpleNamespace:
    defaults = {
        "slug": "newsletter-growth-automation",
        "title": "Newsletter Growth Automation",
        "description": "Automate subscriber growth with verified guardrails.",
        "markdown_body": (
            "---\n"
            "name: newsletter-growth\n"
            "description: Growth loops for indie newsletters\n"
            "---\n\n"
            "# Newsletter Growth\n\n"
            "When to use: weekly newsletter ops.\n\n"
            "1. Research audience pain\n"
            "2. Draft sequence\n"
            "3. Simulate before send\n"
        ),
        "verified_at": datetime.now(tz=UTC),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_assess_tenant_skill_sellable_when_valid_then_sellable() -> None:
    result = assess_tenant_skill_sellable(_skill())  # type: ignore[arg-type]
    assert result.tier == "sellable"
    assert result.recommended_for_launch is True


def test_assess_tenant_skill_sellable_when_generic_slug_then_draft_or_rejected() -> None:
    result = assess_tenant_skill_sellable(_skill(slug="skill-factory-draft"))  # type: ignore[arg-type]
    assert result.tier in {"draft", "rejected"}
    assert "generic_factory_slug" in result.issues


def test_launch_queue_sort_key_accepts_pydantic_out() -> None:
    from app.application.services.skill_factory_sellable import launch_queue_sort_key

    a = SimpleNamespace(sellable_score=0.9, title="Alpha")
    b = SimpleNamespace(sellable_score=0.5, title="Beta")
    assert launch_queue_sort_key(a) < launch_queue_sort_key(b)


def test_assess_tenant_skill_sellable_when_forge_quality_failed_then_not_recommended() -> None:
    result = assess_tenant_skill_sellable(
        _skill(),  # type: ignore[arg-type]
        forge_quality={"quality_gate_passed": False, "critic_approved": False},
    )
    assert result.recommended_for_launch is False
    assert "forge_quality_gate_failed" in result.issues
