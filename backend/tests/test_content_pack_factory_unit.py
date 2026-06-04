"""Content Pack Factory unit tests."""

from __future__ import annotations

import json

from app.application.services.content_pack_factory_quality_gate import (
    evaluate_content_pack_outputs,
    validate_content_pack_artifact,
)
from app.application.services.content_pack_factory_forge import is_content_pack_factory_session
from app.application.services.content_pack_factory_research import _score_opportunity
from app.application.services.content_pack_factory_service import (
    build_content_pack_factory_session_goal,
    slugify_content_pack_name,
)
from app.application.services.publish_pack import PUBLISH_PACK_FORMAT


def _sample_pack_payload() -> dict:
    return {
        "format": PUBLISH_PACK_FORMAT,
        "artifact_type": "publish_pack",
        "channel": "instagram",
        "title": "Coach calendar pack",
        "body": "A" * 120,
        "hashtags": ["coaching", "content"],
        "cta": "Start your free trial",
        "simulate_only": True,
        "snippets": [
            {"text": "Hook one for coaches", "cta": "Learn more", "hashtags": ["coach"]},
            {"text": "Hook two for coaches", "cta": "Learn more", "hashtags": ["growth"]},
            {"text": "Hook three for coaches", "cta": "Learn more", "hashtags": ["tips"]},
        ],
    }


def test_slugify_content_pack_name() -> None:
    assert slugify_content_pack_name("Instagram Calendar Pack!") == "instagram-calendar-pack"
    assert slugify_content_pack_name("   ") == "content-pack-output"


def test_score_opportunity_composite_in_range() -> None:
    demand, competition, buildability, composite, rationale = _score_opportunity(
        niche="Instagram content calendar for coaches",
        hive_hits=2,
        existing_count=1,
        library_count=0,
    )
    assert 0.0 <= demand <= 1.0
    assert 0.0 <= composite <= 1.0
    assert "Demand" in rationale


def test_build_session_goal_includes_quality_gate() -> None:
    from types import SimpleNamespace

    opp = SimpleNamespace(
        niche="TikTok hooks",
        title="TikTok hook library",
        rationale="High demand",
    )
    goal = build_content_pack_factory_session_goal(opportunity=opp, price_cents=1900)
    assert "TikTok hooks" in goal
    assert "content-pack-factory-ready" in goal
    assert "Critic verdict: APPROVE" in goal
    assert "secret" not in goal.lower()
    assert "token" not in goal.lower()


def test_validate_content_pack_artifact_passes() -> None:
    ok, issues, pack = validate_content_pack_artifact(_sample_pack_payload())
    assert ok is True
    assert issues == []
    assert pack is not None
    assert pack.simulate_only is True


def test_evaluate_content_pack_outputs_requires_critic() -> None:
    payload = _sample_pack_payload()
    coder = f"```json\n{json.dumps(payload)}\n```"
    critic = "Critic verdict: APPROVE — content-pack-factory-ready"
    result = evaluate_content_pack_outputs(coder_output=coder, critic_output=critic)
    assert result.passed is True
    assert result.pack_valid is True
    assert result.critic_approved is True


def test_is_content_pack_factory_session() -> None:
    from types import SimpleNamespace

    session = SimpleNamespace(goal="Content Pack Factory — build pack", context_summary={})
    assert is_content_pack_factory_session(session) is True
    other = SimpleNamespace(goal="Regular task", context_summary={})
    assert is_content_pack_factory_session(other) is False
