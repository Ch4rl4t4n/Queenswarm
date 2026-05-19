"""xAI Grok Voice Agent — ephemeral client tokens for browser realtime sessions."""

from __future__ import annotations

import httpx

from app.application.services.llm_runtime_credentials import provider_effective_grok
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_CLIENT_SECRETS_URL = "https://api.x.ai/v1/realtime/client_secrets"


class XaiVoiceLiveError(RuntimeError):
    """Raised when xAI Voice Agent token minting fails."""


async def mint_voice_live_client_secret(*, ttl_seconds: int = 300) -> dict[str, object]:
    """Mint a short-lived client secret for browser WebSocket voice sessions.

    Args:
        ttl_seconds: Token lifetime (xAI default window; max per their API docs).

    Returns:
        Dict with ``value`` (token string) and ``expires_at`` (unix timestamp).

    Raises:
        XaiVoiceLiveError: When Grok key is missing or xAI rejects the request.
    """

    grok_key = provider_effective_grok()
    if not grok_key:
        raise XaiVoiceLiveError("Grok API key not configured — add it in Settings → LLM keys.")

    ttl = max(60, min(ttl_seconds, settings.ballroom_voice_live_token_ttl_sec))
    async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=4.0)) as client:
        response = await client.post(
            _CLIENT_SECRETS_URL,
            headers={"Authorization": f"Bearer {grok_key}", "Content-Type": "application/json"},
            json={"expires_after": {"seconds": ttl}},
        )

    if response.status_code >= 400:
        detail = response.text[:240]
        logger.warning("xai.voice_live.token_failed", status=response.status_code, detail=detail)
        raise XaiVoiceLiveError(f"xAI voice token failed: {response.status_code} {detail}")

    body = response.json()
    if not isinstance(body, dict):
        raise XaiVoiceLiveError("xAI voice token returned invalid JSON.")
    token_value = body.get("value")
    if not isinstance(token_value, str) or not token_value.strip():
        raise XaiVoiceLiveError("xAI voice token missing value field.")
    logger.info("xai.voice_live.token_ok", expires_at=body.get("expires_at"))
    return body
