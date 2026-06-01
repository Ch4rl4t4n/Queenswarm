"""Unit tests for social intel Grok truth gate."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.social_intel_truth_gate import (
    TruthArbiterVerdict,
    claims_pass_hivemind_gate,
    verify_intel_claim_via_grok,
    _parse_verdict_json,
)


def test_parse_verdict_json_from_fenced_block() -> None:
    raw = """```json
{"claim": "x", "source": "u", "verdict": "true", "confidence": "high", "reason": "ok"}
```"""
    verdict = _parse_verdict_json(raw, claim="x", source="u")
    assert verdict.verdict == "true"
    assert verdict.allows_hivemind_write() is True


def test_claims_pass_hivemind_gate_rejects_false() -> None:
    verdicts = [
        TruthArbiterVerdict(verdict="true", confidence="high"),
        TruthArbiterVerdict(verdict="false", confidence="high"),
    ]
    assert claims_pass_hivemind_gate(verdicts) is False


def test_claims_pass_hivemind_gate_accepts_partial_medium() -> None:
    verdicts = [TruthArbiterVerdict(verdict="partial", confidence="medium")]
    assert claims_pass_hivemind_gate(verdicts) is True


@pytest.mark.asyncio
async def test_verify_intel_claim_via_grok_uses_router() -> None:
    router = MagicMock()
    router.complete_with_fallback_messages = AsyncMock(
        return_value=(
            json.dumps(
                {
                    "claim": "Tool X works",
                    "source": "https://youtube.com/watch?v=1",
                    "verdict": "false",
                    "confidence": "high",
                    "reason": "unverified hype",
                    "corroboration": None,
                },
            ),
            0.001,
        ),
    )
    verdict = await verify_intel_claim_via_grok(
        claim="Tool X works",
        source_url="https://youtube.com/watch?v=1",
        router=router,
    )
    assert verdict.verdict == "false"
    assert verdict.allows_hivemind_write() is False
    router.complete_with_fallback_messages.assert_awaited_once()
