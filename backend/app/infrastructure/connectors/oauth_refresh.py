"""Minimal OAuth2 refresh-token exchange without third-party identity brokers."""

from __future__ import annotations

from typing import Any

import httpx

from app.infrastructure.connectors.base import ConnectorAuthEnvelope
from app.infrastructure.connectors.secure_vault import CredentialPayload
from app.core.retry_external import retry_async_call
from app.core.logging import get_logger

logger = get_logger(__name__)


async def exchange_refresh_token(auth: ConnectorAuthEnvelope) -> tuple[CredentialPayload, dict[str, Any]]:
    """POST ``grant_type=refresh_token`` against ``oauth2_token_endpoint``.

    Args:
        auth: Envelope pointing at issuer token URL + refresh secret.

    Returns:
        Updated credential payload and raw JSON blob for dashboards.

    Raises:
        ValueError: Missing refresh configuration.
        httpx.HTTPError: Upstream rejects the refresh call (after retries).
    """

    if not auth.oauth2_refresh_token or not auth.oauth2_token_endpoint:
        msg = "OAuth2 refresh requires refresh token and token endpoint on the credential envelope."
        raise ValueError(msg)

    endpoint = auth.oauth2_token_endpoint.strip()
    form: dict[str, str] = {
        "grant_type": "refresh_token",
        "refresh_token": auth.oauth2_refresh_token.strip(),
    }
    if isinstance(auth.oauth2_client_id, str) and auth.oauth2_client_id.strip():
        form["client_id"] = auth.oauth2_client_id.strip()
    if isinstance(auth.oauth2_client_secret, str) and auth.oauth2_client_secret.strip():
        form["client_secret"] = auth.oauth2_client_secret.strip()

    async with httpx.AsyncClient(timeout=30.0) as client:

        async def post_form() -> httpx.Response:
            response = await client.post(endpoint, data=form)
            response.raise_for_status()
            return response

        rsp = await retry_async_call(post_form)
        data = rsp.json()

    access = data.get("access_token")
    if not isinstance(access, str) or not access.strip():
        msg = "Token endpoint omitted access_token."
        raise ValueError(msg)

    refreshed: str | None = auth.oauth2_refresh_token.strip()
    if isinstance(data.get("refresh_token"), str) and data["refresh_token"].strip():
        refreshed = data["refresh_token"].strip()

    payload = CredentialPayload(
        kind="oauth2",
        oauth2_access_token=access.strip(),
        oauth2_refresh_token=refreshed,
        oauth2_token_endpoint=auth.oauth2_token_endpoint,
        oauth2_client_id=auth.oauth2_client_id,
        oauth2_client_secret=auth.oauth2_client_secret,
        api_key=None,
        scopes=tuple(auth.scopes),
    )

    logger.info(
        "connector.oauth_refresh.success",
        agent_id="connector-oauth",
        swarm_id="refresh",
        task_id="token-endpoint",
    )
    return payload, data


__all__ = ["exchange_refresh_token"]
