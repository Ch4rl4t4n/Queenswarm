"""Compatibility ``/llm-keys`` surface backed by the hive LLM vault + operator metadata."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError

from app.presentation.api.deps import DashboardSession, DbSession
from app.core.jwt_tokens import parse_dashboard_user_subject
from app.core.logging import get_logger
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.application.services.llm_runtime_credentials import (
    delete_llm_provider_secret,
    get_cached_llm_key,
    persist_llm_provider_secret,
    provider_effective_anthropic,
    provider_effective_grok,
    provider_effective_openai,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/llm-keys", tags=["LLM Keys"])

ProviderLiteral = Literal["grok", "anthropic", "openai"]


class LLMKeyCreateBody(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    provider: ProviderLiteral
    label: str = Field(default="Primary", min_length=2, max_length=160)
    api_key: str = Field(..., min_length=12, max_length=2048)
    model_default: str | None = Field(default=None, max_length=160)
    is_primary: bool = Field(default=True)


class LLMKeyMask(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    provider: ProviderLiteral
    label: str
    api_key_masked: str
    model_default: str | None
    is_active: bool = True
    is_primary: bool = True
    from_vault: bool = False


def _user_uuid(sess: dict[str, Any]) -> uuid.UUID:
    raw_sub = sess.get("sub")
    if not isinstance(raw_sub, str):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard subject missing.")
    resolved = parse_dashboard_user_subject(raw_sub.strip())
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Malformed dashboard identity.")
    return resolved


def _mask(secret: str) -> str:
    trimmed = secret.strip()
    if len(trimmed) < 4:
        return "••••••••"
    return "••••••••" + trimmed[-4:]


def _meta_prefs(user: DashboardUser) -> dict[str, Any]:
    prefs = dict(user.notification_prefs or {})
    bucket = prefs.get("llm_operator_labels")
    if isinstance(bucket, dict):
        return prefs
    prefs["llm_operator_labels"] = {}
    return prefs


def _provider_label_model(user: DashboardUser, provider: str) -> tuple[str, str | None]:
    prefs = _meta_prefs(user)
    labels = prefs.get("llm_operator_labels")
    if not isinstance(labels, dict):
        return provider.title(), None
    meta = labels.get(provider)
    if isinstance(meta, dict):
        label = meta.get("label") if isinstance(meta.get("label"), str) else provider.title()
        model = meta.get("model_default") if isinstance(meta.get("model_default"), str) else None
        return str(label), model
    return provider.title(), None


@router.get("/", summary="Masked LLM credentials for the operator console")
async def list_llm_operator_keys(sess: DashboardSession, db: DbSession) -> dict[str, Any]:
    """Summarize env + vault secrets without revealing plaintext."""

    uid = _user_uuid(sess)
    user = await db.get(DashboardUser, uid)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive operator.")

    keys: list[dict[str, Any]] = []
    triplets: list[tuple[ProviderLiteral, str, Any]] = [
        ("grok", provider_effective_grok(), get_cached_llm_key("grok")),
        ("anthropic", provider_effective_anthropic(), get_cached_llm_key("anthropic")),
        ("openai", provider_effective_openai(), get_cached_llm_key("openai")),
    ]

    for provider, effective, vault_val in triplets:
        if not effective:
            continue
        label, model_default = _provider_label_model(user, provider)
        keys.append(
            LLMKeyMask(
                id=f"vault-{provider}",
                provider=provider,
                label=label,
                api_key_masked=_mask(effective),
                model_default=model_default,
                is_active=True,
                is_primary=True,
                from_vault=bool(vault_val),
            ).model_dump(),
        )

    return {"keys": keys}


@router.post("/", summary="Upsert an LLM provider secret (delegates to hive vault)")
async def create_llm_operator_key(
    body: LLMKeyCreateBody,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, Any]:
    """Persist ciphertext for ``grok`` (any operator) or Anthropic/OpenAI (admin only)."""

    uid = _user_uuid(sess)
    user = await db.get(DashboardUser, uid)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive operator.")

    if body.provider != "grok" and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required.")

    try:
        await persist_llm_provider_secret(db, provider=body.provider, plaintext=body.api_key)
        prefs = _meta_prefs(user)
        labels = dict(prefs["llm_operator_labels"]) if isinstance(prefs.get("llm_operator_labels"), dict) else {}
        labels[body.provider] = {
            "label": body.label.strip(),
            "model_default": body.model_default.strip() if body.model_default else None,
            "is_primary": body.is_primary,
        }
        prefs["llm_operator_labels"] = labels
        user.notification_prefs = prefs
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not persist LLM credentials.",
        ) from None

    logger.info(
        "llm_keys.operator_upsert",
        agent_id=str(uid),
        swarm_id="",
        task_id="",
        provider=body.provider,
    )
    return {"status": "created", "id": body.provider, "provider": body.provider}


@router.delete("/{provider}", summary="Remove a provider secret from the vault")
async def delete_llm_operator_key(
    provider: ProviderLiteral,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, Any]:
    uid = _user_uuid(sess)
    user = await db.get(DashboardUser, uid)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive operator.")
    if provider != "grok" and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required.")

    try:
        await delete_llm_provider_secret(db, provider=provider)
        prefs = dict(user.notification_prefs or {})
        labels = prefs.get("llm_operator_labels")
        if isinstance(labels, dict) and provider in labels:
            labels = dict(labels)
            labels.pop(provider, None)
            prefs["llm_operator_labels"] = labels
            user.notification_prefs = prefs
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not delete LLM credential.",
        ) from None

    return {"status": "deleted", "provider": provider}


@router.post("/test/{provider}", summary="Fire a one-token LiteLLM ping for a provider")
async def test_llm_operator_key(
    provider: ProviderLiteral,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, Any]:
    uid = _user_uuid(sess)
    user = await db.get(DashboardUser, uid)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive operator.")
    if provider != "grok" and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required.")

    _, model_hint = _provider_label_model(user, provider)
    defaults: dict[ProviderLiteral, str] = {
        "grok": "xai/grok-3-mini",
        "anthropic": "anthropic/claude-haiku-4-5-20251001",
        "openai": "openai/gpt-4o-mini",
    }
    model = (model_hint or defaults[provider]).strip()

    try:
        from litellm import completion

        resp = completion(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: CONNECTED"}],
            max_tokens=6,
        )
        text = (resp.choices[0].message.content or "").strip()
        return {"status": "ok", "model": model, "response": text}
    except Exception as exc:  # noqa: BLE001 — surfaced to operator UI
        logger.warning(
            "llm_keys.test_failed",
            agent_id=str(uid),
            swarm_id="",
            task_id="",
            provider=provider,
            error=str(exc),
        )
        return {"status": "error", "error": str(exc), "model": model}
