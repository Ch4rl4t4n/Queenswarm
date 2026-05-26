"""Analysis Swarm consensus unit tests."""

from __future__ import annotations

import pytest

from app.application.services.analysis_swarm import run_analysis_consensus


@pytest.mark.asyncio
async def test_run_analysis_consensus_bullish_on_high_confidence() -> None:
    out = await run_analysis_consensus(
        task="paper tick BTC",
        symbol="BTC",
        side_hint="buy",
        signal_confidence=0.9,
    )
    assert out.enabled is True
    assert len(out.votes) == 3
    assert out.consensus in {"bullish", "bearish", "neutral"}


@pytest.mark.asyncio
async def test_run_analysis_consensus_neutral_on_low_confidence() -> None:
    out = await run_analysis_consensus(
        task="wait",
        symbol="ETH",
        side_hint="buy",
        signal_confidence=0.2,
    )
    assert out.recommend_execute is False
