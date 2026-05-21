"""Unit tests for Slack harness trainer — signature, merge, validation."""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.slack_harness_trainer import (
    SlackHarnessTrainerValidationError,
    format_slack_feedback_block,
    merge_instructions_append,
    verify_slack_request_signature,
)


def test_verify_slack_request_signature_accepts_valid_digest() -> None:
    """Official signing protocol should accept matching v0 digest."""

    secret = "test-signing-secret"
    body = b"token=x&text=Always+verify+simulations&user_name=alice"
    timestamp = str(int(time.time()))
    basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    digest = hmac.new(secret.encode("utf-8"), basestring.encode("utf-8"), hashlib.sha256).hexdigest()
    assert verify_slack_request_signature(
        signing_secret=secret,
        timestamp=timestamp,
        body=body,
        signature=f"v0={digest}",
    )


def test_verify_slack_request_signature_rejects_stale_timestamp() -> None:
    """Requests older than five minutes must fail."""

    secret = "test-signing-secret"
    body = b"text=hi"
    stale = str(int(time.time()) - 600)
    basestring = f"v0:{stale}:{body.decode('utf-8')}"
    digest = hmac.new(secret.encode("utf-8"), basestring.encode("utf-8"), hashlib.sha256).hexdigest()
    assert not verify_slack_request_signature(
        signing_secret=secret,
        timestamp=stale,
        body=body,
        signature=f"v0={digest}",
    )


def test_format_slack_feedback_block_uses_bullets() -> None:
    """Each non-empty line becomes a markdown bullet."""

    block = format_slack_feedback_block(
        feedback="Line one\nLine two",
        author="alice",
        source="dashboard",
    )
    assert "## Slack feedback ·" in block
    assert "- Line one" in block
    assert "- Line two" in block


def test_merge_instructions_append_trims_oldest_slack_blocks() -> None:
    """When over budget, drop oldest Slack feedback sections."""

    existing = "## Slack feedback · old\n\n- drop me\n\n" + ("x" * 7900)
    block = format_slack_feedback_block(feedback="new rule", author="bob", source="slack")
    merged = merge_instructions_append(existing, block, max_chars=8000)
    assert len(merged) <= 8000
    assert "new rule" in merged
    assert "drop me" not in merged


def test_merge_instructions_append_raises_when_preamble_too_large() -> None:
    """Non-Slack preamble that alone exceeds budget should error."""

    existing = "x" * 8001
    block = format_slack_feedback_block(feedback="tiny", author="a", source="dashboard")
    with pytest.raises(SlackHarnessTrainerValidationError):
        merge_instructions_append(existing, block)


@pytest.mark.asyncio
async def test_append_behavioral_feedback_requires_min_length() -> None:
    """Too-short feedback is rejected before persistence."""

    from app.application.services.slack_harness_trainer import append_behavioral_feedback

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    with patch(
        "app.application.services.slack_harness_trainer.assert_slack_trainer_allowed",
        new_callable=AsyncMock,
    ):
        with pytest.raises(SlackHarnessTrainerValidationError, match="4 characters"):
            await append_behavioral_feedback(
                session,
                tenant_id=tenant_id,
                feedback="hi",
                source="dashboard",
            )
