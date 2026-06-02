"""Grok truth arbiter for social intel — verify claims before HiveMind promotion."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.llm_router import LiteLLMRouter
from app.core.logging import get_logger

logger = get_logger(__name__)

_GROK_MODEL = "xai/grok-3-mini"
_TRUTH_ARBITER_SYSTEM = """\
You are a truth arbiter for an AI agent swarm. Given a claim extracted from a public
YouTube video summary and its source URL, respond with JSON only (no markdown fences):

{
  "claim": "<atomic claim>",
  "source": "<url>",
  "verdict": "true|false|partial|insufficient_evidence",
  "confidence": "high|medium|low",
  "reason": "<one sentence>",
  "corroboration": "<url or null>"
}

Rules:
- verdict=false when the claim is likely wrong, unverifiable hype, or non-functional advice.
- verdict=partial when directionally right but overstated or missing caveats.
- Do not approve tool names, pricing, or "works out of the box" claims without corroboration.
"""


class TruthArbiterVerdict(BaseModel):
    """Structured Grok truth-arbiter response."""

    model_config = ConfigDict(extra="ignore")

    claim: str = ""
    source: str = ""
    verdict: str = Field(default="insufficient_evidence")
    confidence: str = Field(default="low")
    reason: str = ""
    corroboration: str | None = None

    def allows_hivemind_write(self) -> bool:
        """Return True when claim may be promoted to HiveMind."""

        verdict = self.verdict.strip().lower()
        confidence = self.confidence.strip().lower()
        if verdict == "false":
            return False
        if verdict == "true" and confidence in {"high", "medium"}:
            return True
        return verdict == "partial" and confidence in {"high", "medium"}


def _parse_verdict_json(raw: str, *, claim: str, source: str) -> TruthArbiterVerdict:
    """Parse LLM JSON output with safe fallback."""

    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return TruthArbiterVerdict(
                claim=str(payload.get("claim") or claim),
                source=str(payload.get("source") or source),
                verdict=str(payload.get("verdict") or "insufficient_evidence"),
                confidence=str(payload.get("confidence") or "low"),
                reason=str(payload.get("reason") or ""),
                corroboration=payload.get("corroboration"),
            )
    except json.JSONDecodeError:
        pass
    return TruthArbiterVerdict(claim=claim, source=source, verdict="insufficient_evidence", confidence="low", reason="parse_failed")


async def verify_intel_claim_via_grok(
    *,
    claim: str,
    source_url: str,
    tenant_id: uuid.UUID | None = None,
    task_id: str | None = None,
    router: LiteLLMRouter | None = None,
) -> TruthArbiterVerdict:
    """Run one Grok cross-check on a single factual claim."""

    cleaned_claim = claim.strip()
    if not cleaned_claim:
        return TruthArbiterVerdict(claim="", source=source_url, verdict="insufficient_evidence", confidence="low")

    llm = router or LiteLLMRouter()
    user_prompt = (
        f"Claim: {cleaned_claim}\n"
        f"Source URL: {source_url}\n\n"
        "Is this claim realistic and truthful based on public knowledge? Answer JSON only."
    )
    try:
        content, _cost = await llm.complete_with_fallback_messages(
            messages=[
                {"role": "system", "content": _TRUTH_ARBITER_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            primary_model=_GROK_MODEL,
            tenant_id=tenant_id,
            task_id=task_id or "social-intel-truth-gate",
            agent_id="social_intel_truth_gate",
            swarm_id=str(tenant_id or "social-intel"),
        )
        verdict = _parse_verdict_json(str(content or ""), claim=cleaned_claim, source=source_url)
        logger.info(
            "social_intel.truth_gate.verdict",
            agent_id="social_intel_truth_gate",
            swarm_id=str(tenant_id or ""),
            task_id=task_id or "social-intel-truth-gate",
            verdict=verdict.verdict,
            confidence=verdict.confidence,
            allows=verdict.allows_hivemind_write(),
        )
        return verdict
    except Exception as exc:
        logger.warning(
            "social_intel.truth_gate.failed",
            agent_id="social_intel_truth_gate",
            swarm_id=str(tenant_id or ""),
            error=str(exc)[:200],
        )
        return TruthArbiterVerdict(
            claim=cleaned_claim,
            source=source_url,
            verdict="insufficient_evidence",
            confidence="low",
            reason=f"grok_error:{str(exc)[:120]}",
        )


async def verify_intel_claims_batch(
    claims: list[str],
    *,
    source_url: str,
    tenant_id: uuid.UUID | None = None,
    task_id: str | None = None,
    max_claims: int = 5,
) -> list[TruthArbiterVerdict]:
    """Verify up to N atomic claims from one scraped item."""

    router = LiteLLMRouter()
    out: list[TruthArbiterVerdict] = []
    for claim in claims[:max_claims]:
        out.append(
            await verify_intel_claim_via_grok(
                claim=claim,
                source_url=source_url,
                tenant_id=tenant_id,
                task_id=task_id,
                router=router,
            ),
        )
    return out


def claims_pass_hivemind_gate(verdicts: list[TruthArbiterVerdict]) -> bool:
    """True when at least one claim passes and none are hard-false."""

    if not verdicts:
        return False
    if any(v.verdict.strip().lower() == "false" for v in verdicts):
        return False
    return any(v.allows_hivemind_write() for v in verdicts)


__all__ = [
    "TruthArbiterVerdict",
    "claims_pass_hivemind_gate",
    "verify_intel_claim_via_grok",
    "verify_intel_claims_batch",
]
