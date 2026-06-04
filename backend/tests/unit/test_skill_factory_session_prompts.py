"""Unit tests for Skill Factory session prompt blocks."""

from __future__ import annotations

from app.application.services.skill_factory_session_prompts import (
    build_coder_factory_execute_instruction,
    build_critic_factory_execute_instruction,
    build_critic_factory_user_block,
    is_skill_factory_context,
)


def test_is_skill_factory_context_from_summary_flag() -> None:
    assert is_skill_factory_context({"skill_factory": True}) is True
    assert is_skill_factory_context({"raw_goal": "Skill Factory — produce skill"}) is True
    assert is_skill_factory_context({"raw_goal": "Regular task"}) is False


def test_build_critic_factory_user_block_requires_verdict_line() -> None:
    block = build_critic_factory_user_block(coder_draft="# Draft\n\n1. Step")
    assert "Critic verdict: APPROVE" in block
    assert "Critic verdict: REJECT" in block


def test_build_critic_factory_execute_instruction_blocks_hivemind_format() -> None:
    text = build_critic_factory_execute_instruction()
    assert "Do not return HiveMind" in text
    assert "[INSIGHT]" not in text
    assert "Critic verdict: APPROVE" in text
    assert "Critic verdict: REJECT" in text


def test_should_enqueue_only_first_sub_agent_for_factory() -> None:
    from app.application.services.supervisor.hivemind_verify import should_enqueue_only_first_sub_agent

    assert should_enqueue_only_first_sub_agent({"skill_factory": True}) is True
    assert should_enqueue_only_first_sub_agent({"raw_goal": "Skill Factory — build"}) is True
    assert should_enqueue_only_first_sub_agent({"raw_goal": "Regular task"}) is False


def test_build_coder_factory_execute_instruction_requires_skill_fence() -> None:
    text = build_coder_factory_execute_instruction()
    assert "SKILL.md" in text
    assert "skill-factory-ready" in text
