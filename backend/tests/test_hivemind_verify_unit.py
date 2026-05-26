"""Unit tests for HiveMind researcher → critic verification gate."""

from __future__ import annotations

from app.application.services.supervisor.hivemind_verify import (
    critic_verdict_approved,
    enable_hivemind_verify_seed,
    is_hivemind_verify_session,
)


def test_enable_hivemind_verify_seed_when_researcher_and_critic() -> None:
    seed = enable_hivemind_verify_seed(roles=["researcher", "critic"])
    assert seed["hivemind_verify_before_ingest"] is True
    assert is_hivemind_verify_session(seed) is True


def test_critic_verdict_approved_when_explicit_approved() -> None:
    assert critic_verdict_approved("## Verification verdict: APPROVED") is True


def test_critic_verdict_approved_when_rejected_then_false() -> None:
    text = "## Verification verdict: REJECTED — missing source URLs"
    assert critic_verdict_approved(text) is False


def test_critic_verdict_approved_when_missing_verdict_then_false() -> None:
    assert critic_verdict_approved("Looks good but no verdict line.") is False
