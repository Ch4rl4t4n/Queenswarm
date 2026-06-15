"""Unit tests for public marketing eval (REV2)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.marketing_public_eval import (
    MarketingPublicEvalBody,
    check_marketing_public_eval_rate_limit,
    run_marketing_public_eval,
)


@pytest.mark.asyncio
async def test_run_marketing_public_eval_heuristic_only() -> None:
    body = MarketingPublicEvalBody(
        title="Test",
        workflow_markdown=(
            "---\nname: test-workflow\ndescription: Eval test harness\n---\n\n"
            "# Title\n\nWhen to use: testing.\n\n1. Step one\n2. Step two\n3. Step three\n"
            "\n## Guardrails\n\nSimulate-first only.\n"
        ),
    )
    result = await run_marketing_public_eval(body)
    assert result.eval_report_md
    assert isinstance(result.passed, bool)


@pytest.mark.asyncio
async def test_check_rate_limit_blocks_when_full(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "marketing_public_eval_enabled", True)
    monkeypatch.setattr(config.settings, "marketing_public_eval_rate_limit", 2)
    with patch(
        "app.application.services.marketing_public_eval.sliding_window_reserve",
        AsyncMock(return_value=False),
    ):
        allowed, detail = await check_marketing_public_eval_rate_limit(client_key="1.2.3.4")
    assert allowed is False
    assert "limit" in detail.lower()


@pytest.mark.asyncio
async def test_check_rate_limit_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "marketing_public_eval_enabled", False)
    allowed, _ = await check_marketing_public_eval_rate_limit(client_key="x")
    assert allowed is False
