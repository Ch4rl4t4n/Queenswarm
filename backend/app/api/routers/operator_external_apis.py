"""Operator-scoped external data feed credentials (`operator_external_apis` table)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from cryptography.fernet import InvalidToken
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.deps import DashboardSession, DbSession
from app.core.jwt_tokens import parse_dashboard_user_subject
from app.core.logging import get_logger
from app.models.dashboard_user import DashboardUser
from app.models.operator_external_api import OperatorExternalApi
from app.services.operator_external_api_crypto import decrypt_credentials_blob, encrypt_credentials_blob

logger = get_logger(__name__)

router = APIRouter(prefix="/external-apis", tags=["External APIs"])

_SUPPORTED_PROVIDERS: dict[str, dict[str, Any]] = {
    "alpaca": {"label": "Alpaca Markets", "base_url": "https://paper-api.alpaca.markets"},
    "twitter": {"label": "Twitter / X API"},
    "yahoo": {"label": "Yahoo Finance"},
    "coingecko": {"label": "CoinGecko"},
    "newsapi": {"label": "NewsAPI", "base_url": "https://newsapi.org"},
    "reddit": {"label": "Reddit API"},
    "youtube": {"label": "YouTube Data API v3"},
}


def _dashboard_user_id(sess: dict[str, Any]) -> uuid.UUID:
    raw_sub = sess.get("sub")
    if not isinstance(raw_sub, str):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard subject missing.")
    resolved = parse_dashboard_user_subject(raw_sub.strip())
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Malformed dashboard identity.")
    return resolved


def _mask_credentials(creds: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in creds.items():
        if isinstance(val, str) and val.strip():
            s = val.strip()
            suffix = s[-4:] if len(s) >= 4 else ""
            out[str(key)] = f"••••{suffix}" if suffix else "••••"
        else:
            out[str(key)] = val
    return out


class ExternalApiCreateBody(BaseModel):
    """Create an encrypted credential bundle."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    provider: Literal[
        "alpaca",
        "twitter",
        "yahoo",
        "coingecko",
        "newsapi",
        "reddit",
        "youtube",
    ] = Field(..., description="Known provider slug.")
    label: str = Field(..., min_length=2, max_length=160)
    credentials: dict[str, Any] = Field(default_factory=dict)
    base_url: str | None = Field(default=None, max_length=512)


@router.get("/providers", summary="Catalog of supported external providers")
async def list_supported_providers() -> dict[str, Any]:
    """Expose static provider metadata for Neon settings UIs."""

    return {
        "providers": [
            {"id": slug, "label": meta["label"], "base_url": meta.get("base_url")}
            for slug, meta in sorted(_SUPPORTED_PROVIDERS.items())
        ],
    }


@router.get("/", summary="List operator external API rows (masked credentials)")
async def list_operator_external_apis(sess: DashboardSession, db: DbSession) -> dict[str, Any]:
    """Return encrypted rows with redacted credential fields."""

    uid = _dashboard_user_id(sess)
    principal = await db.get(DashboardUser, uid)
    if principal is None or not principal.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive operator.")

    stmt = (
        select(OperatorExternalApi)
        .where(OperatorExternalApi.user_id == uid)
        .order_by(OperatorExternalApi.created_at.desc())
    )
    rows = list((await db.scalars(stmt)).all())
    apis: list[dict[str, Any]] = []
    for row in rows:
        try:
            creds = decrypt_credentials_blob(row.ciphertext)
        except (InvalidToken, ValueError, UnicodeError):
            creds = {}
        apis.append(
            {
                "id": str(row.id),
                "provider": row.provider,
                "label": row.label,
                "is_active": row.is_active,
                "base_url": row.base_url,
                "credentials_masked": _mask_credentials(creds),
            },
        )
    return {"apis": apis}


@router.post("/", summary="Persist external API credentials (Fernet encrypted JSON)")
async def create_operator_external_api(
    body: ExternalApiCreateBody,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, Any]:
    """Encrypt JSON credentials and persist a row for the active operator."""

    uid = _dashboard_user_id(sess)
    principal = await db.get(DashboardUser, uid)
    if principal is None or not principal.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive operator.")

    if body.provider not in _SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown provider.")

    try:
        ciphertext = encrypt_credentials_blob(body.credentials)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not serialize credentials: {exc}",
        ) from exc

    row = OperatorExternalApi(
        user_id=uid,
        provider=body.provider,
        label=body.label.strip(),
        ciphertext=ciphertext,
        base_url=body.base_url.strip() if body.base_url else None,
        is_active=True,
    )
    db.add(row)
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A credential with this provider + label already exists.",
        ) from None
    except SQLAlchemyError:
        await db.rollback()
        logger.exception(
            "external_apis.persist_failed",
            agent_id=str(uid),
            swarm_id="",
            task_id="",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not persist external API row.",
        ) from None

    logger.info(
        "external_apis.created",
        agent_id=str(uid),
        swarm_id="",
        task_id="",
        provider=body.provider,
    )
    return {"status": "created", "id": str(row.id)}


@router.delete("/{api_id}", summary="Remove an external credential row")
async def delete_operator_external_api(
    api_id: uuid.UUID,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, str]:
    """Delete a row owned by the operator."""

    uid = _dashboard_user_id(sess)
    row = await db.get(OperatorExternalApi, api_id)
    if row is None or row.user_id != uid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    try:
        await db.delete(row)
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not delete external API row.",
        ) from None

    return {"status": "deleted"}
