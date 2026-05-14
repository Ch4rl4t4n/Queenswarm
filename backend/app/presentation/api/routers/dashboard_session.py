"""Human dashboard login surfaces (password + TOTP + refresh tokens)."""

from __future__ import annotations

import json
import re
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, status
from jose import JWTError
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import Response

from app.presentation.api.deps import DashboardAdmin, DashboardSession, DbSession, JwtSubject
from app.core.config import settings
from app.core.llm_router import _openai_key_looks_configured
from app.core.jwt_tokens import (
    create_dashboard_access_token,
    create_pre_2fa_token,
    decode_jwt_optional_typ,
    parse_dashboard_user_subject,
)
from app.core.logging import get_logger
from app.core.redis_client import fetch_dashboard_refresh_user, revoke_dashboard_refresh, store_dashboard_refresh
from app.infrastructure.persistence.models.dashboard_api_key import DashboardApiKey
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.application.services.dashboard_api_keys import (
    API_KEY_PREFIX,
    DashboardApiKeyError,
    create_dashboard_api_key,
    list_dashboard_api_keys,
    normalize_api_key_source_name,
    revoke_dashboard_api_key,
)
from app.application.services.dashboard_crypto import (
    backup_codes_hashed,
    consume_matching_backup_code,
    hash_dashboard_password,
    mint_plain_backup_codes,
    mint_totp_secret,
    totp_uri_for_email,
    totp_verify,
    verify_dashboard_password,
)
from app.application.services.llm_runtime_credentials import (
    delete_llm_provider_secret,
    get_cached_llm_key,
    persist_llm_provider_secret,
    provider_effective_anthropic,
    provider_effective_grok,
    provider_effective_openai,
)

logger = get_logger(__name__)
router = APIRouter(tags=["Auth"])


class _TokenBundle(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class LoginResponse(BaseModel):
    requires_totp: bool
    pre_auth_token: str | None = None
    tokens: _TokenBundle | None = None
    message: str | None = Field(
        default=None,
        description="Optional UX hint after password succeeds but TOTP is still required.",
    )

    @computed_field
    @property
    def requires_2fa(self) -> bool:
        """Alias for dashboards that probe ``requires_2fa`` instead of ``requires_totp``."""

        return self.requires_totp

    @computed_field
    @property
    def mfa_required(self) -> bool:
        """Alias for OTP-gated dashboards that probe ``mfa_required``."""

        return self.requires_totp


class Verify2FARequest(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    pre_auth_token: str = Field(
        ...,
        validation_alias=AliasChoices("pre_auth_token", "mfa_token", "temp_token"),
    )
    totp_code: str = Field(
        ...,
        min_length=6,
        max_length=16,
        validation_alias=AliasChoices("totp_code", "code"),
    )


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=16)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=16)


class DashboardUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    display_name: str | None = None
    is_admin: bool = False
    enable_totp: bool = Field(
        default=True,
        description="When True, provisioning mints ``totp_secret`` so authenticator onboarding is mandatory.",
    )


def _scopes_for(user: DashboardUser) -> str:
    bits = ["dash:read", "dash:operator"]
    if user.is_admin:
        bits.extend(["dash:admin", "dash:recipe_write"])
    return " ".join(sorted(set(bits)))


async def _issue_pair(db_user: DashboardUser) -> dict[str, Any]:
    scopes = _scopes_for(db_user)
    access, ttl = create_dashboard_access_token(
        user_id=db_user.id,
        email=db_user.email,
        scopes=scopes,
    )
    refresh_plain = secrets.token_urlsafe(48)
    ttl_sec = settings.refresh_token_expire_days * 86_400
    await store_dashboard_refresh(refresh_plain, str(db_user.id), ttl_sec)
    logger.info(
        "dashboard_auth.tokens_minted",
        agent_id="dashboard_auth",
        swarm_id="",
        task_id="",
        subject=str(db_user.id),
    )
    return {
        "access_token": access,
        "refresh_token": refresh_plain,
        "expires_in": ttl,
        "token_type": "bearer",
    }


@router.post(
    "/login",
    summary="Authenticate with password (second factor may be required afterward)",
)
async def dashboard_login(body: LoginRequest, db: DbSession) -> LoginResponse:
    stmt = select(DashboardUser).where(DashboardUser.email == body.email.strip().lower())
    try:
        user = await db.scalar(stmt)
    except SQLAlchemyError:
        logger.exception(
            "dashboard_auth.login.lookup_failed",
            agent_id="dashboard_auth",
            swarm_id="",
            task_id="",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth persistence unavailable.",
        )

    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    if not verify_dashboard_password(body.password, user.password_hash):
        logger.warning(
            "dashboard_auth.login.bad_password",
            agent_id="dashboard_auth",
            swarm_id="",
            task_id="",
            email_hash=str(user.email),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    # Challenge TOTP only when enrollment is finished (Authenticator confirmed once).
    # Pending rows (`totp_secret` set, `totp_verified_at` null) must still reach the dashboard
    # to scan the QR — password-only gate here; legacy `totp_required` alone must not trap users on OTP UX.
    if user.totp_secret is not None and user.totp_verified_at is not None:
        pre, _ttl = create_pre_2fa_token(user_id=user.id, email=user.email)
        return LoginResponse(
            requires_totp=True,
            pre_auth_token=pre,
            tokens=None,
            message="Enter your 2FA code",
        )

    bundle_dict = await _issue_pair(user)
    return LoginResponse(requires_totp=False, tokens=_TokenBundle.model_validate(bundle_dict))


@router.post("/verify-2fa", summary="Finalize login by validating an authenticator code")
async def dashboard_verify_totp(body: Verify2FARequest, db: DbSession) -> _TokenBundle:
    try:
        payload = decode_jwt_optional_typ(body.pre_auth_token.strip())
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid pre-auth token.")

    if payload.get("typ") != "pre_2fa":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a pending 2FA token.")

    sub_raw = payload.get("sub")
    try:
        user_id = uuid.UUID(str(sub_raw))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Corrupt identity reference.")

    try:
        user = await db.get(DashboardUser, user_id)
    except SQLAlchemyError:
        logger.exception(
            "dashboard_auth.verify.lookup_failed",
            agent_id="dashboard_auth",
            swarm_id="",
            task_id="",
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persistence error.")

    if user is None or not user.is_active or user.totp_secret is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticator not provisioned.")

    totp_ok = totp_verify(user.totp_secret, body.totp_code)
    if not totp_ok:
        prefs = dict(user.notification_prefs or {})
        raw_hashes = prefs.get("totp_backup_code_hashes")
        hashes = [str(h) for h in raw_hashes] if isinstance(raw_hashes, list) else []
        new_hashes = consume_matching_backup_code(hashes, body.totp_code)
        if new_hashes is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP.")
        prefs["totp_backup_code_hashes"] = new_hashes
        prefs["totp_backup_last_used_at"] = datetime.now(tz=UTC).isoformat()
        user.notification_prefs = prefs

    user.totp_verified_at = datetime.now(tz=UTC)
    try:
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError:
        await db.rollback()
        logger.exception(
            "dashboard_auth.verify.persist_failed",
            agent_id="dashboard_auth",
            swarm_id="",
            task_id="",
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not persist verification.")

    bundle = await _issue_pair(user)
    return _TokenBundle.model_validate(bundle)


@router.post("/totp/verify", summary="Alias for POST /auth/verify-2fa (TOTP or backup code)")
async def dashboard_totp_verify_alias(body: Verify2FARequest, db: DbSession) -> _TokenBundle:
    """Finalize login after ``requires_totp`` — same validation as ``/verify-2fa``."""

    return await dashboard_verify_totp(body, db)


@router.post("/refresh", summary="Rotate access token using opaque refresh credential")
async def dashboard_refresh(body: RefreshRequest, db: DbSession) -> _TokenBundle:
    cleaned = body.refresh_token.strip()
    uid_text = await fetch_dashboard_refresh_user(cleaned)
    if uid_text is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh revoked or expired.")
    try:
        user_uuid = uuid.UUID(uid_text)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Corrupt refresh metadata.")

    try:
        user = await db.get(DashboardUser, user_uuid)
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persistence error.")

    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive operator.")

    await revoke_dashboard_refresh(cleaned)
    bundle_dict = await _issue_pair(user)
    return _TokenBundle.model_validate(bundle_dict)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke dashboard refresh credential")
async def dashboard_logout(body: LogoutRequest) -> Response:
    await revoke_dashboard_refresh(body.refresh_token.strip())
    return Response(status_code=status.HTTP_204_NO_CONTENT)





class MeDetailResponse(BaseModel):
    """Operator envelope consumed by Neon settings screens."""

    email: str
    display_name: str | None = None
    timezone: str | None = None
    notification_prefs: dict[str, Any] = Field(default_factory=dict)
    scopes: list[str]
    is_admin: bool
    totp_required: bool
    totp_has_secret: bool
    totp_verified_at: datetime | None
    totp_backup_codes_remaining: int = 0
    totp_backup_last_used_at: datetime | None = None
    audit_log_enabled: bool = True
    totp_enabled: bool = Field(
        description="True when TOTP enrollment exists and operator completed verification.",
    )


async def _current_dashboard_user(sess: dict[str, Any], db: DbSession) -> DashboardUser:
    """Load the Postgres row backing the JWT access token."""

    sub = sess.get("sub")
    if not isinstance(sub, str):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard subject missing.")
    uid = parse_dashboard_user_subject(sub.strip())
    if uid is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed dashboard subject.")
    row = await db.get(DashboardUser, uid)
    if row is None or not row.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard user missing.")
    return row


def _backup_prefs_snapshot(row: DashboardUser) -> tuple[int, datetime | None]:
    """Return remaining backup codes count and last-consumed timestamp."""

    prefs = dict(row.notification_prefs or {})
    raw = prefs.get("totp_backup_code_hashes")
    n = len(raw) if isinstance(raw, list) else 0
    ts_raw = prefs.get("totp_backup_last_used_at")
    ts: datetime | None = None
    if isinstance(ts_raw, str):
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except ValueError:
            ts = None
    return n, ts


def _audit_log_pref(row: DashboardUser) -> bool:
    prefs = dict(row.notification_prefs or {})
    return bool(prefs.get("audit_log_enabled", True))


def _serialize_me(row: DashboardUser) -> MeDetailResponse:
    """Map ORM rows to public profile envelope."""

    remaining, backup_last = _backup_prefs_snapshot(row)
    return MeDetailResponse(
        email=row.email,
        display_name=row.display_name,
        timezone=row.timezone,
        notification_prefs=dict(row.notification_prefs or {}),
        scopes=sorted(set(_scopes_for(row).split())),
        is_admin=bool(row.is_admin),
        totp_required=bool(row.totp_required),
        totp_has_secret=row.totp_secret is not None,
        totp_verified_at=row.totp_verified_at,
        totp_enabled=bool(row.totp_secret is not None and row.totp_verified_at is not None),
        totp_backup_codes_remaining=remaining,
        totp_backup_last_used_at=backup_last,
        audit_log_enabled=_audit_log_pref(row),
    )


@router.get("/me", summary="Echo dashboard profile + prefs from JWT access tokens")
async def dashboard_me_detail(sess: DashboardSession, db: DbSession) -> MeDetailResponse:
    user = await _current_dashboard_user(sess, db)
    return _serialize_me(user)


class ProfilePatchBody(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    display_name: str | None = Field(default=None, max_length=160)
    timezone: str | None = Field(default=None, max_length=96)


@router.patch("/me/profile", summary="Patch display labels or hive timezone identifiers")
async def dashboard_patch_profile(
    body: ProfilePatchBody,
    sess: DashboardSession,
    db: DbSession,
) -> MeDetailResponse:
    user = await _current_dashboard_user(sess, db)
    mutated = False
    if body.display_name is not None:
        trimmed_name = body.display_name.strip()
        user.display_name = trimmed_name[:160] if trimmed_name else None
        mutated = True
    if body.timezone is not None:
        trimmed_tz = body.timezone.strip()
        user.timezone = trimmed_tz[:96] if trimmed_tz else None
        mutated = True
    if not mutated:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one mutable field.",
        )
    try:
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError:
        await db.rollback()
        logger.exception(
            "dashboard_auth.profile_patch_failed",
            agent_id=str(user.id),
            swarm_id="",
            task_id="",
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persistence error.")
    return _serialize_me(user)


_CHANNEL_PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-]{5,21}$")


def normalize_delivery_channels_blob(existing: Any) -> dict[str, Any]:
    """Coerce nullable or JSON-string legacy ``delivery_channels`` into a plain dict."""

    if isinstance(existing, dict):
        return dict(existing)
    if isinstance(existing, str) and existing.strip():
        try:
            parsed = json.loads(existing)
        except ValueError:
            return {}
        if isinstance(parsed, dict):
            return dict(parsed)
        return {}
    return {}


_DISCORD_WEBHOOK_HOSTS: frozenset[str] = frozenset(
    {
        "discord.com",
        "discordapp.com",
        "ptb.discord.com",
        "canary.discord.com",
    },
)


def discord_webhook_url_ok(url: str) -> bool:
    """True for official Discord webhook HTTPS URLs only (no ``*-discord.com`` typosquats)."""

    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    if host not in _DISCORD_WEBHOOK_HOSTS:
        return False
    return path.startswith("/api/webhooks/")


class EmailChannelConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    enabled: bool = False
    label: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=254)

    @field_validator("address", mode="before")
    @classmethod
    def strip_addr(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("address must be a string")
        s = value.strip()
        return s or None


class SmsChannelConfig(BaseModel):
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    enabled: bool = False
    label: str | None = Field(default=None, max_length=120)
    phone_e164: str | None = Field(default=None, max_length=32)

    @field_validator("phone_e164", mode="before")
    @classmethod
    def strip_phone(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("phone_e164 must be a string")
        s = value.strip()
        if not s:
            return None
        if not _CHANNEL_PHONE_RE.match(s):
            raise ValueError("phone_e164 looks invalid (use E.164-style, e.g. +421901234567)")
        return s


class DiscordChannelConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    enabled: bool = False
    label: str | None = Field(default=None, max_length=120)
    webhook_url: str | None = Field(default=None, max_length=2048)

    @field_validator("webhook_url", mode="before")
    @classmethod
    def validate_webhook(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("webhook_url must be a string")
        s = value.strip()
        if not s:
            return None
        if not discord_webhook_url_ok(s):
            raise ValueError(
                "Discord webhook must be an https URL under discord.com (or discordapp.com) /api/webhooks/",
            )
        return s


class TelegramChannelConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    enabled: bool = False
    label: str | None = Field(default=None, max_length=120)
    bot_token: str | None = Field(default=None, max_length=256)
    chat_id: str | None = Field(default=None, max_length=64)

    @field_validator("bot_token", "chat_id", mode="before")
    @classmethod
    def strip_opt(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("value must be a string")
        s = value.strip()
        return s or None


class DeliveryChannelsMerge(BaseModel):
    """Partial update for ``notification_prefs['delivery_channels']``."""

    model_config = ConfigDict(extra="ignore")

    email: EmailChannelConfig | None = None
    sms: SmsChannelConfig | None = None
    discord: DiscordChannelConfig | None = None
    telegram: TelegramChannelConfig | None = None


class NotificationPrefsMergeBody(BaseModel):
    """Merge JSON for ``dashboard_users.notification_prefs`` (channels + legacy keys)."""

    model_config = ConfigDict(extra="allow")

    delivery_channels: DeliveryChannelsMerge | None = None


def _merge_delivery_buckets(existing: Any, merge: DeliveryChannelsMerge) -> dict[str, Any]:
    base: dict[str, Any] = normalize_delivery_channels_blob(existing)
    dumped = merge.model_dump(exclude_unset=True)
    for ch_name in ("email", "sms", "discord", "telegram"):
        ch_patch = dumped.get(ch_name)
        if ch_patch is None:
            continue
        prev_raw = base.get(ch_name)
        prev: dict[str, Any] = dict(prev_raw) if isinstance(prev_raw, dict) else {}
        prev.update(ch_patch)
        base[ch_name] = prev
    return base


@router.patch("/me/notifications", summary="Merge notification preferences (channels + legacy flags)")
async def dashboard_patch_notifications(
    body: NotificationPrefsMergeBody,
    sess: DashboardSession,
    db: DbSession,
) -> MeDetailResponse:
    user = await _current_dashboard_user(sess, db)
    merged: dict[str, Any] = dict(user.notification_prefs or {})
    raw_dump = body.model_dump(exclude_unset=True)
    dc_raw = raw_dump.pop("delivery_channels", None)
    if dc_raw is not None:
        dm = DeliveryChannelsMerge.model_validate(dc_raw)
        merged["delivery_channels"] = _merge_delivery_buckets(merged.get("delivery_channels"), dm)
    for key, val in raw_dump.items():
        merged[key] = val
    user.notification_prefs = merged
    try:
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError:
        await db.rollback()
        logger.exception(
            "dashboard_auth.notification_prefs_failed",
            agent_id=str(user.id),
            swarm_id="",
            task_id="",
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persistence error.")
    return _serialize_me(user)


class LLMProvidersStatus(BaseModel):
    grok_configured: bool
    anthropic_configured: bool
    openai_configured: bool
    grok_from_vault: bool = False
    anthropic_from_vault: bool = False
    openai_from_vault: bool = False


@router.get(
    "/integrations/llm-providers",
    summary="Reveal which LiteLLM routes are live (env + optional dashboard vault)",
)
async def integrations_llm_status(_subject: JwtSubject) -> LLMProvidersStatus:
    grok_eff = provider_effective_grok()
    anth_eff = provider_effective_anthropic()
    open_eff = provider_effective_openai()
    return LLMProvidersStatus(
        grok_configured=bool(grok_eff),
        anthropic_configured=bool(anth_eff),
        openai_configured=_openai_key_looks_configured(open_eff),
        grok_from_vault=bool(get_cached_llm_key("grok")),
        anthropic_from_vault=bool(get_cached_llm_key("anthropic")),
        openai_from_vault=bool(get_cached_llm_key("openai")),
    )


class LlmVaultRotateBody(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    api_key: str = Field(..., min_length=12, max_length=2048)


@router.post(
    "/integrations/llm-providers/{provider}/secret",
    summary="Store encrypted LLM secret (Grok: any operator; Claude/OpenAI: admin only)",
)
async def vault_set_llm_provider_secret(
    provider: Literal["grok", "anthropic", "openai"],
    body: LlmVaultRotateBody,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, bool]:
    user = await _current_dashboard_user(sess, db)
    if provider != "grok" and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required.")
    try:
        await persist_llm_provider_secret(db, provider=provider, plaintext=body.api_key)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not persist LLM secret.",
        ) from None
    logger.info(
        "dashboard_auth.llm_vault_rotated",
        agent_id="operator_hub",
        swarm_id="",
        task_id="",
        provider=provider,
    )
    return {"ok": True}


@router.delete(
    "/integrations/llm-providers/{provider}/secret",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove vault LLM secret (Grok: any operator; others: admin only)",
)
async def vault_clear_llm_provider_secret(
    provider: Literal["grok", "anthropic", "openai"],
    sess: DashboardSession,
    db: DbSession,
) -> Response:
    user = await _current_dashboard_user(sess, db)
    if provider != "grok" and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required.")
    try:
        await delete_llm_provider_secret(db, provider=provider)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not clear LLM secret.",
        ) from None
    logger.info(
        "dashboard_auth.llm_vault_cleared",
        agent_id="operator_hub",
        swarm_id="",
        task_id="",
        provider=provider,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class PasswordConfirmBody(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    password: str = Field(..., min_length=8, max_length=256)


class TotpCodeBody(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    code: str = Field(..., min_length=6, max_length=12)


class TwoFAProvisionResponse(BaseModel):
    secret_base32: str
    otpauth_uri: str


def _provision_response(user: DashboardUser) -> TwoFAProvisionResponse:
    """Return otpauth provisioning metadata for UX QR rendering."""

    assert user.totp_secret is not None
    uri = totp_uri_for_email(issuer=settings.dashboard_totpissuer, email=user.email, secret=user.totp_secret)
    return TwoFAProvisionResponse(secret_base32=user.totp_secret, otpauth_uri=uri)


@router.post(
    "/profile/totp/provision",
    summary="Mint a fresh TOTP secret after password confirmation",
    response_model=TwoFAProvisionResponse,
)
async def profile_totp_provision(
    body: PasswordConfirmBody,
    sess: DashboardSession,
    db: DbSession,
) -> TwoFAProvisionResponse:
    user = await _current_dashboard_user(sess, db)
    if not verify_dashboard_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password.")
    user.totp_secret = mint_totp_secret()
    user.totp_verified_at = None
    user.totp_required = True
    prefs = dict(user.notification_prefs or {})
    prefs.pop("totp_backup_code_hashes", None)
    prefs.pop("totp_backup_last_used_at", None)
    user.notification_prefs = prefs
    try:
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not persist provisioning material.",
        ) from None
    return _provision_response(user)


class TotpConfirmResponse(BaseModel):
    """Result of completing authenticator enrollment."""

    verified: bool = True
    backup_codes: list[str] | None = None


@router.post(
    "/profile/totp/confirm",
    summary="Finalize authenticator enrollment with a numeric OTP",
    response_model=TotpConfirmResponse,
)
async def profile_totp_confirm(body: TotpCodeBody, sess: DashboardSession, db: DbSession) -> TotpConfirmResponse:
    user = await _current_dashboard_user(sess, db)
    if user.totp_secret is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP provisioning has not started.")
    if not totp_verify(user.totp_secret, body.code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP.")
    was_new = user.totp_verified_at is None
    user.totp_verified_at = datetime.now(tz=UTC)
    user.totp_required = True
    backup_codes: list[str] | None = None
    if was_new:
        prefs = dict(user.notification_prefs or {})
        existing = prefs.get("totp_backup_code_hashes")
        if not isinstance(existing, list) or len(existing) == 0:
            plain = mint_plain_backup_codes()
            prefs["totp_backup_code_hashes"] = backup_codes_hashed(plain)
            user.notification_prefs = prefs
            backup_codes = plain
    try:
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from None
    return TotpConfirmResponse(verified=True, backup_codes=backup_codes)


@router.post(
    "/profile/totp/backup-codes/regenerate",
    summary="Replace backup codes after password confirmation (plaintext returned once)",
)
async def profile_totp_backup_regenerate(
    body: PasswordConfirmBody,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, list[str]]:
    user = await _current_dashboard_user(sess, db)
    if not verify_dashboard_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password.")
    if user.totp_secret is None or user.totp_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete TOTP enrollment before managing backup codes.",
        )
    plain = mint_plain_backup_codes()
    prefs = dict(user.notification_prefs or {})
    prefs["totp_backup_code_hashes"] = backup_codes_hashed(plain)
    user.notification_prefs = prefs
    try:
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from None
    logger.info(
        "dashboard_auth.totp_backup_regenerated",
        agent_id=str(user.id),
        swarm_id="",
        task_id="",
    )
    return {"codes": plain}


@router.post("/profile/totp/disable", summary="Strip authenticator enrollment after verifying password")
async def profile_totp_disable(body: PasswordConfirmBody, sess: DashboardSession, db: DbSession) -> MeDetailResponse:
    user = await _current_dashboard_user(sess, db)
    if not verify_dashboard_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password.")
    user.totp_required = False
    user.totp_verified_at = None
    user.totp_secret = None
    prefs = dict(user.notification_prefs or {})
    prefs.pop("totp_backup_code_hashes", None)
    prefs.pop("totp_backup_last_used_at", None)
    user.notification_prefs = prefs
    try:
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from None
    logger.info(
        "dashboard_auth.totp_disabled_self",
        agent_id=str(user.id),
        swarm_id="",
        task_id="",
    )
    return _serialize_me(user)


class ApiKeyCreateBody(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    source_name: str = Field(..., min_length=2, max_length=80)
    label: str | None = Field(default=None, max_length=160)

    @field_validator("source_name")
    @classmethod
    def _slugify_source_name(cls, value: str) -> str:
        return normalize_api_key_source_name(value)


class ApiKeySummary(BaseModel):
    id: uuid.UUID
    source_name: str | None
    label: str | None
    masked_prefix: str
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None


class ApiKeyMinted(ApiKeySummary):
    plaintext: str


def _mask_key_row(row: DashboardApiKey) -> ApiKeySummary:
    masked = f"{API_KEY_PREFIX}{row.id.hex[:10]}•••"
    return ApiKeySummary(
        id=row.id,
        source_name=row.source_name,
        label=row.label,
        masked_prefix=masked,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
        revoked_at=row.revoked_at,
    )


@router.get("/api-keys", summary="List bcrypt-protected scripted credentials tied to this operator")
async def list_dashboard_api_credentials(sess: DashboardSession, db: DbSession) -> list[ApiKeySummary]:
    user = await _current_dashboard_user(sess, db)
    rows = await list_dashboard_api_keys(db, user_id=user.id)
    active = [r for r in rows if r.revoked_at is None]
    return [_mask_key_row(row) for row in active]


@router.post("/api-keys", summary="Create a scripted credential returned once")
async def create_dashboard_api_credential_route(
    body: ApiKeyCreateBody,
    sess: DashboardSession,
    db: DbSession,
) -> ApiKeyMinted:
    user = await _current_dashboard_user(sess, db)
    try:
        row, plaintext = await create_dashboard_api_key(
            db,
            user_id=user.id,
            source_name=body.source_name,
            label=body.label,
        )
        await db.commit()
        await db.refresh(row)
    except DashboardApiKeyError as exc:
        await db.rollback()
        detail = str(exc)
        lowered = detail.lower()
        if "already exists" in lowered:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
        if "maximum" in lowered and "api keys" in lowered:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail) from exc
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from None
    base = _mask_key_row(row).model_dump()
    return ApiKeyMinted(**base, plaintext=plaintext)


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke scripted credential fingerprints",
)
async def revoke_dashboard_api_credential_route(
    key_id: uuid.UUID,
    sess: DashboardSession,
    db: DbSession,
) -> Response:
    user = await _current_dashboard_user(sess, db)
    try:
        await revoke_dashboard_api_key(db, user_id=user.id, key_id=key_id)
        await db.commit()
    except DashboardApiKeyError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class _AdminUserMade(BaseModel):
    id: uuid.UUID
    email: str


@router.post(
    "/admin/users",
    response_model=_AdminUserMade,
    status_code=status.HTTP_201_CREATED,
    summary="Provision a dashboard user (requires dash:admin scope)",
)
async def admin_create_dashboard_user(body: DashboardUserCreate, db: DbSession, _: DashboardAdmin) -> _AdminUserMade:
    email_key = body.email.strip().lower()
    exists_stmt = select(DashboardUser.id).where(DashboardUser.email == email_key)

    dup = await db.scalar(exists_stmt)
    if dup is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already enrolled.")

    totp_secret = mint_totp_secret() if body.enable_totp else None
    entity = DashboardUser(
        email=email_key,
        password_hash=hash_dashboard_password(body.password),
        display_name=body.display_name,
        totp_secret=totp_secret,
        totp_verified_at=None,
        totp_required=bool(body.enable_totp and totp_secret),
        is_admin=body.is_admin,
        is_active=True,
    )
    try:
        db.add(entity)
        await db.flush()
        await db.commit()
        await db.refresh(entity)
    except SQLAlchemyError:
        await db.rollback()
        logger.exception(
            "dashboard_auth.admin_create_failed",
            agent_id="dashboard_auth",
            swarm_id="",
            task_id="",
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.")

    return _AdminUserMade(id=entity.id, email=entity.email)


@router.post("/2fa/setup", summary="Administrators regenerate TOTP material for their login")
async def setup_totp(sess: DashboardSession, db: DbSession) -> TwoFAProvisionResponse:
    scopes_raw = str(sess.get("scope", ""))
    if "dash:admin" not in scopes_raw.split():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrators only.")
    row = await _current_dashboard_user(sess, db)
    row.totp_secret = mint_totp_secret()
    row.totp_required = True
    await db.commit()
    await db.refresh(row)
    logger.info(
        "dashboard_auth.totp_reprovisioned",
        agent_id=str(row.id),
        swarm_id="",
        task_id="",
        email_hash=row.email,
    )
    return _provision_response(row)


__all__ = ["router"]
