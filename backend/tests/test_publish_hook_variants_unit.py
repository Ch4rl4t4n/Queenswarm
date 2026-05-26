"""Publish hook variants — deterministic generation."""

from __future__ import annotations

from app.application.services.publish_hook_variants import generate_publish_hook_variants


def test_generate_publish_hook_variants_from_title() -> None:
    variants = generate_publish_hook_variants(
        title="Queenswarm growth",
        body="We built a bee-hive agent swarm. Here is what we learned.",
        channel="instagram",
    )
    assert len(variants) >= 3
    hooks = {v["hook"].lower() for v in variants}
    assert len(hooks) == len(variants)
    assert any("queenswarm" in h for h in hooks)


def test_generate_publish_hook_variants_tiktok_pov() -> None:
    variants = generate_publish_hook_variants(
        title="Trading paper mode",
        body="Paper trading lets you test signals safely.",
        channel="tiktok",
    )
    styles = {v["style"] for v in variants}
    assert "pov" in styles


def test_generate_publish_hook_variants_deduplicates() -> None:
    variants = generate_publish_hook_variants(
        title="",
        body="",
        channel="twitter",
        max_variants=8,
    )
    assert len(variants) <= 8
