"""Unit tests for ST1 supervisor session discipline (OP1 / LN1)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.application.services.supervisor_session_discipline import (
    critic_failure_blocks_auto_approve,
    mark_discipline_failure_summary,
    session_has_critic_failure,
    session_has_llm_failure,
)


def test_session_has_critic_failure_from_summary_flag() -> None:
    assert session_has_critic_failure(context_summary={"critic_failure": True}) is True


def test_session_has_critic_failure_from_hivemind_rejected() -> None:
    assert session_has_critic_failure(context_summary={"hivemind_verify_status": "rejected"}) is True


def test_session_has_critic_failure_from_critic_sub_reject() -> None:
    sub = SimpleNamespace(role="critic", short_memory={"last_summary": "Critic verdict: reject\nDetails"})
    assert session_has_critic_failure(context_summary={}, sub_agents=[sub]) is True


def test_session_has_critic_failure_when_critic_approves_then_false() -> None:
    sub = SimpleNamespace(role="critic", short_memory={"last_summary": "Critic verdict: approve\nOK"})
    assert session_has_critic_failure(context_summary={}, sub_agents=[sub]) is False


def test_session_has_llm_failure_from_summary() -> None:
    assert session_has_llm_failure(context_summary={"llm_failure": True}) is True
    assert session_has_llm_failure(context_summary={"self_heal_exhausted": True}) is True


def test_session_has_llm_failure_from_sub_agent_error() -> None:
    sub = MagicMock()
    sub.error_text = "Self-healing exhausted after 3 attempts"
    sub.short_memory = {}
    sub.last_output = ""
    assert session_has_llm_failure(context_summary={}, sub_agents=[sub]) is True


def test_critic_failure_blocks_auto_approve_when_llm_failed() -> None:
    blocked = critic_failure_blocks_auto_approve(
        goal="test",
        context_summary={"llm_failure": True},
        sub_agents=None,
    )
    assert blocked is True


def test_mark_discipline_failure_summary_stamps_reasons() -> None:
    out = mark_discipline_failure_summary({}, reason="same_failure_twice", detail="repeat sig")
    assert out["same_failure_twice"] is True
    assert out["discipline_halt_reason"] == "repeat sig"
