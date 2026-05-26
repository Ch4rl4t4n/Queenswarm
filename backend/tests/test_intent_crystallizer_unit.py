"""Unit tests for Intent Crystallizer v2."""

from __future__ import annotations

from app.application.services.intent_crystallizer import (
    compose_intent_crystallizer_snapshot,
    crystallize_intent,
    format_crystallized_telegram,
)


def test_crystallize_intent_factory_template() -> None:
    plan = crystallize_intent("Build micro SaaS landing for PDF tool")
    assert "micro-saas-factory" in plan.suggested_templates
    assert plan.trust_lane == "simulate"
    assert plan.primary_href == "/factory"
    assert plan.deep_links.get("factory") == "/factory"


def test_crystallize_intent_research_auto_lane() -> None:
    plan = crystallize_intent("Research competitor pricing brief")
    assert plan.trust_lane == "auto"


def test_crystallize_intent_content_template() -> None:
    plan = crystallize_intent("Create TikTok marketing content for launch")
    assert "content-flywheel-v2" in plan.suggested_templates
    assert len(plan.steps) >= 3


def test_format_crystallized_telegram() -> None:
    plan = crystallize_intent("Analyze market trends for Q3")
    text = format_crystallized_telegram(plan, base_url="https://queenswarm.love")
    assert "Intent Crystallizer" in text
    assert "queenswarm.love" in text


def test_compose_snapshot_enabled() -> None:
    snap = compose_intent_crystallizer_snapshot()
    assert snap.enabled is True
    assert len(snap.templates) >= 4
