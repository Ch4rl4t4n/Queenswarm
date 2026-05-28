"""Publish hook variants — deterministic generation."""

from __future__ import annotations

from app.application.services.publish_hook_variants import generate_publish_hook_variants, score_publish_hook_variant


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
    assert all("score" in v and "confidence" in v for v in variants)


def test_generate_publish_hook_variants_deduplicates() -> None:
    variants = generate_publish_hook_variants(
        title="",
        body="",
        channel="twitter",
        max_variants=8,
    )
    assert len(variants) <= 8
    if len(variants) >= 2:
        assert variants[0]["score"] >= variants[1]["score"]


def test_score_publish_hook_variant_thread_weight_for_twitter() -> None:
    thread_score, _ = score_publish_hook_variant(
        channel="twitter",
        style="thread",
        hook="🧵 Quick thread on what changed",
    )
    curiosity_score, _ = score_publish_hook_variant(
        channel="twitter",
        style="curiosity",
        hook="Most teams miss this pattern",
    )
    assert thread_score >= curiosity_score
