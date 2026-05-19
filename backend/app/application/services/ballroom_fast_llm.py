"""Ultra-low-latency Grok completions for live Ballroom orchestrator chat."""

from __future__ import annotations

import httpx

from app.application.services.llm_runtime_credentials import provider_effective_grok
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"


def _resolve_fast_model() -> str:
    """Return the direct xAI model slug for fast ballroom chat."""

    raw = (settings.ballroom_fast_model or "grok-4-fast-non-reasoning").strip()
    if raw.startswith("xai/"):
        return raw[4:]
    return raw


async def grok_ballroom_reply_fast(*, user_text: str, system_prompt: str | None = None) -> str:
    """Single-hop Grok chat — bypasses LiteLLM, DB budget gate, and retry backoff.

    Args:
        user_text: Operator utterance or typed message.
        system_prompt: Optional override; defaults to orchestrator voice persona.

    Returns:
        Assistant text trimmed to a short voice-friendly reply.

    Raises:
        RuntimeError: When Grok credentials are missing or the API rejects the call.
    """

    grok_key = provider_effective_grok()
    if not grok_key:
        raise RuntimeError("Grok credentials missing for fast ballroom lane.")

    model = _resolve_fast_model()
    system = system_prompt or (
        "You are the Queenswarm Orchestrator in live voice chat. "
        "Reply in one or two short spoken sentences. No markdown. Be direct."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text.strip()[:4_000]},
        ],
        "max_tokens": settings.ballroom_fast_max_tokens,
        "temperature": settings.ballroom_fast_temperature,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
        response = await client.post(
            _XAI_CHAT_URL,
            headers={"Authorization": f"Bearer {grok_key}", "Content-Type": "application/json"},
            json=payload,
        )

    if response.status_code >= 400:
        detail = response.text[:240]
        logger.warning("ballroom.fast_llm.failed", model=model, status=response.status_code, detail=detail)
        raise RuntimeError(f"Grok fast chat failed: {response.status_code} {detail}")

    body = response.json()
    choices = body.get("choices") if isinstance(body, dict) else None
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("Grok fast chat returned no choices.")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    text = str(content or "").strip()
    if not text:
        raise RuntimeError("Grok fast chat returned empty content.")
    logger.info("ballroom.fast_llm.ok", model=model, chars=len(text))
    return text
