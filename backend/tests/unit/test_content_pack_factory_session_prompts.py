"""Unit tests for Content Pack Factory session prompt blocks."""

from __future__ import annotations

from app.application.services.content_pack_factory_session_prompts import (
    build_content_pack_coder_execute_instruction,
    build_content_pack_critic_user_block,
    is_content_pack_factory_context,
)


def test_is_content_pack_factory_context_from_summary_flag() -> None:
    assert is_content_pack_factory_context({"content_pack_factory": True}) is True
    assert is_content_pack_factory_context({"raw_goal": "Content Pack Factory — produce pack"}) is True
    assert is_content_pack_factory_context({"raw_goal": "Regular task"}) is False


def test_content_pack_coder_instruction_requires_publish_pack_json() -> None:
    text = build_content_pack_coder_execute_instruction()
    assert "publish_pack" in text
    assert "simulate_only" in text
    assert "LISTING.md" in text
    assert "content-pack-factory-ready" in text
    assert "[INSIGHT]" not in text


def test_content_pack_critic_block_requires_content_pack_verdict() -> None:
    block = build_content_pack_critic_user_block(coder_draft='{"artifact_type":"publish_pack"}')
    assert "Critic verdict: APPROVE" in block
    assert "Critic verdict: REJECT" in block
    assert "publish_pack" in block


def test_should_enqueue_only_first_sub_agent_for_content_pack_factory() -> None:
    from app.application.services.supervisor.hivemind_verify import should_enqueue_only_first_sub_agent

    assert should_enqueue_only_first_sub_agent({"content_pack_factory": True}) is True
    assert should_enqueue_only_first_sub_agent({"raw_goal": "Content Pack Factory — build"}) is True
