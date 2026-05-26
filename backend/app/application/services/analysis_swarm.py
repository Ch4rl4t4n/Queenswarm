"""Analysis Swarm — multi-model consensus bee (simulate-first, P8)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings

AnalysisVote = Literal["bullish", "bearish", "neutral"]


class AnalysisModelVoteOut(BaseModel):
    """One model lane vote."""

    model_config = ConfigDict(extra="ignore")

    model_id: str
    vote: AnalysisVote
    confidence: float
    rationale: str


class AnalysisConsensusOut(BaseModel):
    """Consensus result from Analysis Swarm."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    task: str
    symbol: str
    consensus: AnalysisVote
    consensus_strength: float
    votes: list[AnalysisModelVoteOut] = Field(default_factory=list)
    recommend_execute: bool
    simulate_only: bool = True


def _vote_from_signal(
    *,
    model_id: str,
    side_hint: str,
    confidence: float,
    bias: float,
) -> AnalysisModelVoteOut:
    """Deterministic vote — no live LLM required for default path."""

    adj = max(0.0, min(1.0, confidence + bias))
    side = side_hint.lower()
    if adj >= 0.75 and side in {"buy", "long", "yes"}:
        vote: AnalysisVote = "bullish"
        rationale = f"{model_id}: strong buy signal at {adj:.0%} confidence."
    elif adj >= 0.75 and side in {"sell", "short", "no"}:
        vote = "bearish"
        rationale = f"{model_id}: strong sell signal at {adj:.0%} confidence."
    elif adj >= 0.55:
        vote = "bullish" if side in {"buy", "long", "yes"} else "bearish"
        rationale = f"{model_id}: moderate {side} bias."
    else:
        vote = "neutral"
        rationale = f"{model_id}: insufficient confidence ({adj:.0%}) — wait."
    return AnalysisModelVoteOut(model_id=model_id, vote=vote, confidence=adj, rationale=rationale)


async def run_analysis_consensus(
    *,
    task: str,
    symbol: str,
    side_hint: str = "buy",
    signal_confidence: float = 0.0,
    context: dict[str, Any] | None = None,
) -> AnalysisConsensusOut:
    """Run 3-lane consensus (Grok / Claude / GPT-mini proxies) without mandatory LLM I/O."""

    if not settings.analysis_swarm_enabled:
        return AnalysisConsensusOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            task=task,
            symbol=symbol,
            consensus="neutral",
            consensus_strength=0.0,
            recommend_execute=False,
        )

    ctx = dict(context or {})
    base_conf = float(signal_confidence or ctx.get("confidence") or 0.0)
    side = str(ctx.get("side") or side_hint or "buy")

    votes = [
        _vote_from_signal(model_id="grok-mini", side_hint=side, confidence=base_conf, bias=0.02),
        _vote_from_signal(model_id="claude-haiku", side_hint=side, confidence=base_conf, bias=-0.01),
        _vote_from_signal(model_id="gpt-4o-mini", side_hint=side, confidence=base_conf, bias=0.0),
    ]

    tally = {"bullish": 0, "bearish": 0, "neutral": 0}
    for vote in votes:
        tally[vote.vote] += 1

    consensus = max(tally, key=tally.get)
    strength = tally[consensus] / max(len(votes), 1)
    min_conf = float(settings.analysis_swarm_min_confidence)
    avg_conf = sum(v.confidence for v in votes) / len(votes)
    recommend = consensus in {"bullish", "bearish"} and strength >= 2 / 3 and avg_conf >= min_conf

    return AnalysisConsensusOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        task=task[:500],
        symbol=symbol.upper()[:32],
        consensus=consensus,
        consensus_strength=round(strength, 3),
        votes=votes,
        recommend_execute=recommend,
        simulate_only=True,
    )


__all__ = ["AnalysisConsensusOut", "run_analysis_consensus"]
