"""Machine-safe JWT minting for CI, operators, and LangGraph loaders."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from redis.exceptions import RedisError

from app.common.http.rate_limit import rate_limited_http_exception, rate_limit_unavailable_http_exception
from app.common.http.security_headers import apply_no_store_cache_headers
from app.core.config import settings
from app.core.jwt_tokens import create_access_token
from app.core.logging import get_logger
from app.core.redis_client import sliding_window_reserve
from app.common.schemas.auth import TokenIssued, TokenMintRequest
from app.presentation.api.middleware.rate_limit import peer_ip_for_rate_limit

logger = get_logger(__name__)
router = APIRouter(tags=["Auth"])
_optional_basic = HTTPBasic(auto_error=False)


@dataclass(frozen=True)
class HiveTokenExchangeConfig:
    """Dependency payload describing whether guarded exchange is wired."""

    enabled: bool
    client_id: str
    client_secret: str


def hive_token_exchange_config() -> HiveTokenExchangeConfig:
    """Surface M2M configuration for DI + deterministic FastAPI overrides in tests."""

    cid = settings.hive_token_client_id
    secret = settings.hive_token_client_secret
    active = bool(cid and secret)
    return HiveTokenExchangeConfig(
        enabled=active,
        client_id=(cid.strip() if isinstance(cid, str) else ""),
        client_secret=(secret if isinstance(secret, str) else ""),
    )


@router.post(
    "/token",
    response_model=TokenIssued,
    summary="Mint a short-lived JWT using hive M2M credentials",
)
async def exchange_machine_token(
    body: TokenMintRequest,
    creds: Annotated[HTTPBasicCredentials | None, Depends(_optional_basic)],
    exchange: Annotated[HiveTokenExchangeConfig, Depends(hive_token_exchange_config)],
    request: Request,
    response: Response,
) -> TokenIssued:
    """Return a Bearer token when Basic auth aligns with configured client credentials."""

    if not exchange.enabled:
        logger.warning(
            "auth.token_exchange.disabled_hit",
            agent_id="auth_router",
            swarm_id="",
            task_id="",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hive machine token exchange is not configured.",
        )

    if settings.rate_limit_enabled:
        peer = peer_ip_for_rate_limit(request)
        try:
            token_ok = await sliding_window_reserve(
                f"queenswarm:rl:token_exchange:{peer}",
                limit=settings.rate_limit_token_exchange_max,
                window_sec=settings.rate_limit_token_exchange_window_sec,
            )
        except RedisError as exc:
            logger.warning(
                "auth.token_exchange.ratelimit_redis_degraded",
                agent_id="auth_router",
                swarm_id="",
                task_id="",
                error=str(exc),
                peer=peer,
            )
            if settings.production_security_mode:
                raise rate_limit_unavailable_http_exception(
                    window_sec=settings.rate_limit_token_exchange_window_sec,
                ) from exc
            token_ok = True
        if not token_ok:
            raise rate_limited_http_exception(
                "Token exchange rate limit exceeded.",
                window_sec=settings.rate_limit_token_exchange_window_sec,
            )

    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing HTTP Basic client credentials.",
            headers={"WWW-Authenticate": 'Basic realm="hive-m2m"'},
        )

    user_ok = secrets.compare_digest(
        creds.username.strip().encode("utf-8"),
        exchange.client_id.encode("utf-8"),
    )
    pass_ok = secrets.compare_digest(
        creds.password.encode("utf-8"),
        exchange.client_secret.encode("utf-8"),
    )
    if not (user_ok and pass_ok):
        logger.warning(
            "auth.token_exchange.invalid_credentials",
            agent_id="auth_router",
            swarm_id="",
            task_id="",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials.",
            headers={"WWW-Authenticate": 'Basic realm="hive-m2m"'},
        )

    requested_subject = body.subject.strip()
    subject = requested_subject if settings.hive_token_allow_subject_override else exchange.client_id

    token, expires_in = create_access_token(
        subject=subject,
        expires_minutes=body.expires_minutes,
        scope=body.scope.strip() if body.scope else None,
    )

    logger.info(
        "auth.token_exchange.success",
        agent_id="auth_router",
        swarm_id="",
        task_id="",
        subject=subject,
        requested_subject=requested_subject,
        subject_override=bool(settings.hive_token_allow_subject_override),
        expires_seconds=expires_in,
    )

    apply_no_store_cache_headers(response)
    return TokenIssued(access_token=token, token_type="bearer", expires_in=expires_in)


__all__ = ["HiveTokenExchangeConfig", "hive_token_exchange_config", "router"]
