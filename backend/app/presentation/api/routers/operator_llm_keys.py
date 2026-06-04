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
    provider_effective_deepgram,
    provider_effective_elevenlabs,
    provider_effective_grok,
    provider_effective_openai,
    provider_effective_openrouter,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/llm-keys", tags=["LLM Keys"])

ProviderLiteral = Literal["grok", "anthropic", "openai", "openrouter", "deepgram", "elevenlabs"]
VoiceSttProviderLiteral = Literal["auto", "grok", "deepgram", "openai"]
VoiceTtsProviderLiteral = Literal["auto", "grok", "elevenlabs", "openai"]
VoiceLatencyModeLiteral = Literal["balanced", "fast"]


class LLMKeyCreateBody(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    provider: ProviderLiteral
    label: str = Field(default="", max_length=160)
    api_key: str = Field(..., min_length=12, max_length=2048)
    model_default: str | None = Field(default=None, max_length=160)
    is_primary: bool = Field(default=False)


class LLMKeyMetaBody(BaseModel):
    """Update friendly label / primary flag without rotating the API secret."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    label: str = Field(default="", max_length=160)
    is_primary: bool = False


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


class VoiceProviderPreferences(BaseModel):
    model_config = ConfigDict(extra="ignore")

    stt_provider: VoiceSttProviderLiteral = "auto"
    tts_provider: VoiceTtsProviderLiteral = "auto"
    latency_mode: VoiceLatencyModeLiteral = "fast"
    vad_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    silence_duration_ms: int = Field(default=450, ge=300, le=4000)
    tts_voice_id: str = Field(default="eve", min_length=2, max_length=64)
    tts_language: str = Field(default="auto", min_length=2, max_length=16)
    tts_tone: str = Field(default="none", min_length=2, max_length=32)


class VoiceProviderPreferencesBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    stt_provider: VoiceSttProviderLiteral = "auto"
    tts_provider: VoiceTtsProviderLiteral = "auto"
    latency_mode: VoiceLatencyModeLiteral = "fast"
    vad_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    silence_duration_ms: int = Field(default=450, ge=300, le=4000)
    tts_voice_id: str = Field(default="eve", min_length=2, max_length=64)
    tts_language: str = Field(default="auto", min_length=2, max_length=16)
    tts_tone: str = Field(default="none", min_length=2, max_length=32)


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


def _provider_label_model(user: DashboardUser, provider: str) -> tuple[str, str | None, bool]:
    prefs = _meta_prefs(user)
    labels = prefs.get("llm_operator_labels")
    if not isinstance(labels, dict):
        return "", None, provider == "grok"
    meta = labels.get(provider)
    if isinstance(meta, dict):
        label = meta.get("label") if isinstance(meta.get("label"), str) else ""
        model = meta.get("model_default") if isinstance(meta.get("model_default"), str) else None
        is_primary = bool(meta.get("is_primary")) if "is_primary" in meta else provider == "grok"
        return str(label), model, is_primary
    return "", None, provider == "grok"


def _voice_provider_preferences(user: DashboardUser) -> VoiceProviderPreferences:
    prefs = dict(user.notification_prefs or {})
    raw = prefs.get("voice_provider_preferences")
    if not isinstance(raw, dict):
        return VoiceProviderPreferences()
    stt_raw = raw.get("stt_provider")
    tts_raw = raw.get("tts_provider")
    stt: VoiceSttProviderLiteral = "auto"
    tts: VoiceTtsProviderLiteral = "auto"
    if stt_raw in {"auto", "grok", "deepgram", "openai"}:
        stt = stt_raw
    if tts_raw in {"auto", "grok", "elevenlabs", "openai"}:
        tts = tts_raw
    latency_raw = raw.get("latency_mode")
    latency_mode: VoiceLatencyModeLiteral = "fast"
    if latency_raw in {"balanced", "fast"}:
        latency_mode = latency_raw
    vad_raw = raw.get("vad_threshold")
    vad_threshold = 0.35
    if isinstance(vad_raw, (int, float)) and 0.0 <= float(vad_raw) <= 1.0:
        vad_threshold = float(vad_raw)
    silence_raw = raw.get("silence_duration_ms")
    silence_duration_ms = 450
    if isinstance(silence_raw, int) and 300 <= silence_raw <= 4000:
        silence_duration_ms = silence_raw
    voice_raw = raw.get("tts_voice_id")
    tts_voice_id = voice_raw.strip() if isinstance(voice_raw, str) and voice_raw.strip() else "eve"
    language_raw = raw.get("tts_language")
    tts_language = language_raw.strip() if isinstance(language_raw, str) and language_raw.strip() else "auto"
    tone_raw = raw.get("tts_tone")
    tts_tone = tone_raw.strip() if isinstance(tone_raw, str) and tone_raw.strip() else "none"
    return VoiceProviderPreferences(
        stt_provider=stt,
        tts_provider=tts,
        latency_mode=latency_mode,
        vad_threshold=vad_threshold,
        silence_duration_ms=silence_duration_ms,
        tts_voice_id=tts_voice_id,
        tts_language=tts_language,
        tts_tone=tts_tone,
    )


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
        ("openrouter", provider_effective_openrouter(), get_cached_llm_key("openrouter")),
        ("deepgram", provider_effective_deepgram(), get_cached_llm_key("deepgram")),
        ("elevenlabs", provider_effective_elevenlabs(), get_cached_llm_key("elevenlabs")),
    ]

    for provider, effective, vault_val in triplets:
        if not effective:
            continue
        label, model_default, is_primary = _provider_label_model(user, provider)
        keys.append(
            LLMKeyMask(
                id=f"vault-{provider}",
                provider=provider,
                label=label,
                api_key_masked=_mask(effective),
                model_default=model_default,
                is_active=True,
                is_primary=is_primary,
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
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


@router.patch("/{provider}/meta", summary="Update provider label / primary flag (no secret rotation)")
async def patch_llm_operator_key_meta(
    provider: ProviderLiteral,
    body: LLMKeyMetaBody,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, Any]:
    """Persist operator-facing metadata for a shard without requiring a new API key."""

    uid = _user_uuid(sess)
    user = await db.get(DashboardUser, uid)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive operator.")
    if provider != "grok" and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required.")

    prefs = _meta_prefs(user)
    labels = dict(prefs.get("llm_operator_labels") or {})
    if body.is_primary:
        for key in list(labels.keys()):
            if key == provider:
                continue
            row = labels.get(key)
            if isinstance(row, dict):
                labels[key] = {**row, "is_primary": False}
    labels[provider] = {
        "label": body.label.strip(),
        "model_default": (
            labels.get(provider, {}).get("model_default")
            if isinstance(labels.get(provider), dict)
            else None
        ),
        "is_primary": body.is_primary,
    }
    prefs["llm_operator_labels"] = labels
    user.notification_prefs = prefs
    await db.commit()
    label, model_default, is_primary = _provider_label_model(user, provider)
    return {
        "status": "updated",
        "provider": provider,
        "label": label,
        "model_default": model_default,
        "is_primary": is_primary,
    }


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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
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

    if provider in {"deepgram", "elevenlabs"}:
        effective = get_cached_llm_key(provider)
        if provider == "deepgram" and not effective:
            effective = provider_effective_deepgram()
        if provider == "elevenlabs" and not effective:
            effective = provider_effective_elevenlabs()
        if not effective:
            return {"status": "error", "error": "No credential configured.", "model": provider}
        return {"status": "ok", "model": provider, "response": "CREDENTIAL_READY"}

    _, model_hint, _ = _provider_label_model(user, provider)
    defaults: dict[ProviderLiteral, str] = {
        "grok": "xai/grok-3-mini",
        "anthropic": "anthropic/claude-haiku-4-5-20251001",
        "openai": "openai/gpt-4o-mini",
        "openrouter": "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
        "deepgram": "deepgram/nova-2",
        "elevenlabs": "elevenlabs/tts",
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


@router.get("/voice-preferences", response_model=VoiceProviderPreferences, summary="Get preferred voice providers")
async def get_voice_provider_preferences(
    sess: DashboardSession,
    db: DbSession,
) -> VoiceProviderPreferences:
    uid = _user_uuid(sess)
    user = await db.get(DashboardUser, uid)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive operator.")
    return _voice_provider_preferences(user)


@router.put("/voice-preferences", response_model=VoiceProviderPreferences, summary="Update preferred voice providers")
async def put_voice_provider_preferences(
    body: VoiceProviderPreferencesBody,
    sess: DashboardSession,
    db: DbSession,
) -> VoiceProviderPreferences:
    uid = _user_uuid(sess)
    user = await db.get(DashboardUser, uid)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive operator.")

    prefs = dict(user.notification_prefs or {})
    prefs["voice_provider_preferences"] = {
        "stt_provider": body.stt_provider,
        "tts_provider": body.tts_provider,
        "latency_mode": body.latency_mode,
        "vad_threshold": body.vad_threshold,
        "silence_duration_ms": body.silence_duration_ms,
        "tts_voice_id": body.tts_voice_id,
        "tts_language": body.tts_language,
        "tts_tone": body.tts_tone,
    }
    user.notification_prefs = prefs
    try:
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not save voice provider preferences.",
        ) from None
    return VoiceProviderPreferences(
        stt_provider=body.stt_provider,
        tts_provider=body.tts_provider,
        latency_mode=body.latency_mode,
        vad_threshold=body.vad_threshold,
        silence_duration_ms=body.silence_duration_ms,
        tts_voice_id=body.tts_voice_id,
        tts_language=body.tts_language,
        tts_tone=body.tts_tone,
    )


@router.patch("/voice-preferences", response_model=VoiceProviderPreferences, summary="Update preferred voice providers")
async def patch_voice_provider_preferences(
    body: VoiceProviderPreferencesBody,
    sess: DashboardSession,
    db: DbSession,
) -> VoiceProviderPreferences:
    return await put_voice_provider_preferences(body=body, sess=sess, db=db)
